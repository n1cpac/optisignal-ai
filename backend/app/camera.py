# Camera capture module
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from app.config import ROOT, SETTINGS

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
        if not self.is_image and time.monotonic() - self._frame_time > self.timeout_seconds:
            return None
        return self._frame

    def _run(self) -> None:
        if self.is_image:
            self._load_image()
            return
        while not self._stop.is_set():
            if self._read_until_end():
                self.restarts += 1
            elif not self._stop.is_set():
                logger.warning("Sin senal en la fuente %s", self.source)
                self._stop.wait(RECONNECT_SECONDS)

    def _load_image(self) -> None:
        try:
            # imdecode porque cv2.imread falla con rutas no ASCII en Windows
            self._frame = cv2.imdecode(np.fromfile(self.source, np.uint8), cv2.IMREAD_COLOR)
        except OSError:
            logger.error("No se pudo leer la imagen %s", self.source)

    def _read_until_end(self) -> bool:
        """Lee hasta que la fuente termina. True si un video llego al final y debe repetirse."""
        capture = cv2.VideoCapture(self.source)
        is_file = isinstance(self.source, str)
        if not is_file:
            # Sin esto OpenCV abre las camaras a 640x480 y el semaforo queda en pocos pixeles
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, SETTINGS["camera"]["resolution_width"])
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, SETTINGS["camera"]["resolution_height"])
        frames_read = 0
        try:
            fps = capture.get(cv2.CAP_PROP_FPS) if is_file else 0
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    break
                self._frame, self._frame_time = frame, time.monotonic()
                frames_read += 1
                if fps > 0:
                    self._stop.wait(1 / fps)  # un archivo se lee mas rapido que el tiempo real
        finally:
            capture.release()
        return is_file and frames_read > 0
