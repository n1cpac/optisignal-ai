# Camera capture module
from collections import deque
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from app.config import ROOT, SETTINGS

if os.environ.get("OPTISIGNAL_LOW_MEM") == "1":
    os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "threads;1")
    cv2.setNumThreads(1)

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
RECONNECT_SECONDS = 2.0


class CameraFeed:
    """Mantiene el ultimo frame de una fuente: indice de camara (OBS), video en bucle o imagen fija."""

    def __init__(self, source: Union[int, str], timeout_seconds: float = SETTINGS["camera"]["timeout_seconds"]):
        self.source = source if isinstance(source, int) else str(ROOT / source)
        self.timeout_seconds = timeout_seconds
        self._frame: Optional[np.ndarray] = None
        self._frame_time = 0.0
        self._frame_seq = 0
        self._lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._low_mem = os.environ.get("OPTISIGNAL_LOW_MEM") == "1" and isinstance(source, str)
        self._continuous = threading.Event()
        self._continuous.set()
        self._next_pos = 0
        recent_maxlen = 2 if self._low_mem else 18
        self._recent_frames: deque[tuple[float, int, np.ndarray]] = deque(maxlen=recent_maxlen)
        self.is_image = isinstance(source, str) and Path(source).suffix.lower() in IMAGE_SUFFIXES
        self.restarts = 0  # veces que un video volvio a empezar
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def read(self) -> Optional[np.ndarray]:
        """Ultimo frame, o None si no hay senal: una camara trabada no debe verse como activa."""
        return self.read_with_seq()[0]

    def read_with_seq(self) -> tuple[Optional[np.ndarray], int]:
        """Ultimo frame y su contador de secuencia, o (None, seq) si expiro la senal."""
        frame, _, seq = self.read_stamped()
        return frame, seq

    def read_stamped(self) -> tuple[Optional[np.ndarray], float, int]:
        """Devuelve (frame, frame_time, frame_seq) o (None, ftime, seq) si expiro la senal."""
        now = time.monotonic()
        with self._lock:
            frame, ftime, seq = self._frame, self._frame_time, self._frame_seq
        if not self.is_image and now - ftime > self.timeout_seconds:
            return None, ftime, seq
        return frame, ftime, seq

    def pop_recent_frames(self, after_seq: int, max_seq: Optional[int] = None) -> list[tuple[float, int, np.ndarray]]:
        """Extrae en orden cronologico los cuadros muestreados con seq > after_seq (y <= max_seq si se indica)."""
        with self._lock:
            return [
                item for item in self._recent_frames
                if item[1] > after_seq and (max_seq is None or item[1] <= max_seq)
            ]

    def set_continuous(self, active: bool) -> None:
        """En modo baja memoria, activa o pausa la lectura continua para no mantener decoders FFmpeg inactivos."""
        if not self._low_mem:
            return
        if active:
            self._continuous.set()
        else:
            self._continuous.clear()

    def step_batch_and_release(self, n_frames: int = 4) -> None:
        """Abre el video en la ultima posicion, lee un lote corto y libera el decoder inmediatamente."""
        if self.is_image:
            with self._lock:
                has_frame = self._frame is not None
            if not has_frame:
                self._load_image()
            return
        if not self._low_mem or self._continuous.is_set() or not isinstance(self.source, str):
            return
        with self._io_lock:
            capture = cv2.VideoCapture(self.source)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            restarted = False
            try:
                raw_fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
                target_fps = float(SETTINGS["camera"].get("fps", 15))
                fps = min(raw_fps, target_fps) if raw_fps > 0 else target_fps
                frame_dt = (1.0 / fps) if fps > 0 else (1.0 / 15.0)
                if self._next_pos > 0:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, self._next_pos)
                batch: list[np.ndarray] = []
                for _ in range(max(1, n_frames)):
                    ok, frame = capture.read()
                    if not ok:
                        if self._next_pos > 0:
                            restarted = True
                            self._next_pos = 0
                            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ok, frame = capture.read()
                        if not ok:
                            break
                    batch.append(frame)
                    self._next_pos += 1
                if batch:
                    if restarted:
                        self.restarts += 1
                    now_end = time.monotonic()
                    with self._lock:
                        if restarted:
                            self._recent_frames.clear()
                        total = len(batch)
                        for idx, frame in enumerate(batch):
                            ts = now_end - (total - 1 - idx) * frame_dt
                            self._frame = frame
                            self._frame_time = ts
                            self._frame_seq += 1
                            if idx < total - 1 and idx % 2 == 0:
                                self._recent_frames.append((ts, self._frame_seq, frame))
            finally:
                capture.release()

    def _run(self) -> None:
        if self.is_image:
            self._load_image()
            return
        while not self._stop.is_set():
            if self._low_mem and not self._continuous.is_set():
                self._continuous.wait(timeout=0.3)
                continue
            if self._read_until_end():
                self.restarts += 1
            elif not self._stop.is_set() and (not self._low_mem or self._continuous.is_set()):
                logger.warning("Sin senal en la fuente %s", self.source)
                self._stop.wait(RECONNECT_SECONDS)

    def _load_image(self) -> None:
        try:
            # imdecode porque cv2.imread falla con rutas no ASCII en Windows
            frame = cv2.imdecode(np.fromfile(self.source, np.uint8), cv2.IMREAD_COLOR)
            with self._lock:
                self._frame = frame
                self._frame_time = time.monotonic()
                self._frame_seq += 1
        except OSError:
            logger.error("No se pudo leer la imagen %s", self.source)

    def _read_until_end(self) -> bool:
        """Lee hasta que la fuente termina. True si un video llego al final y debe repetirse."""
        with self._io_lock:
            capture = cv2.VideoCapture(self.source)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            is_file = isinstance(self.source, str)
            if not is_file:
                # Sin esto OpenCV abre las camaras a 640x480 y el semaforo queda en pocos pixeles
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, SETTINGS["camera"]["resolution_width"])
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, SETTINGS["camera"]["resolution_height"])
            elif self._low_mem and self._next_pos > 0:
                capture.set(cv2.CAP_PROP_POS_FRAMES, self._next_pos)
            frames_read = 0
            paused = False
            try:
                raw_fps = capture.get(cv2.CAP_PROP_FPS) if is_file else 0.0
                target_fps = float(SETTINGS["camera"].get("fps", 15))
                fps = min(raw_fps, target_fps) if raw_fps > 0 else target_fps
                frame_interval = (1.0 / fps) if (is_file and fps > 0) else 0.0
                while not self._stop.is_set():
                    if self._low_mem and not self._continuous.is_set():
                        paused = True
                        break
                    frame_start = time.monotonic()
                    ok, frame = capture.read()
                    if not ok:
                        if is_file:
                            self._next_pos = 0
                        break
                    if is_file:
                        self._next_pos += 1
                    now_frame = time.monotonic()
                    with self._lock:
                        if frames_read == 0:
                            self._recent_frames.clear()
                        self._frame = frame
                        self._frame_time = now_frame
                        self._frame_seq += 1
                        frames_read += 1
                        if frames_read % 3 == 1:
                            self._recent_frames.append((now_frame, self._frame_seq, frame))
                    if frame_interval > 0.0:
                        remaining = frame_interval - (time.monotonic() - frame_start)
                        if remaining > 0.0:
                            self._stop.wait(remaining)  # mantiene la velocidad real descontando el tiempo de decodificacion
            finally:
                capture.release()
            return (not paused) and is_file and frames_read > 0
