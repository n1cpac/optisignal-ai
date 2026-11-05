# Ciclo de vision: lee cada camara, detecta, clasifica y deja el resultado listo para la API
import logging
import threading
import time
from datetime import datetime, timezone
from typing import NamedTuple, Optional

import cv2
import numpy as np

from app.camera import CameraFeed
from app.classifier import classify_light
from app.config import SETTINGS
from app.detector import Detection

logger = logging.getLogger(__name__)

VISUAL_STATES = {
    "RED": "rojo",
    "YELLOW": "amarillo",
    "GREEN": "verde",
    "OFF": "apagado",
    "MULTIPLE": "multiple",
    "UNKNOWN": "desconocido",
}
LIGHT_NAMES = {"red": "rojo", "yellow": "amarillo", "green": "verde"}
BOX_COLOR = (255, 111, 30)


class VisionResult(NamedTuple):
    estado_visual: str
    luces: list[str]
    confianza: Optional[float]
    actualizado: str  # ISO 8601
    jpeg: Optional[bytes]  # frame anotado; None mientras no haya senal


def analyze(frame: Optional[np.ndarray], detector) -> VisionResult:
    now = datetime.now(timezone.utc).isoformat()
    if frame is None:
        return VisionResult("sin_senal", [], None, now, None)

    detection: Optional[Detection] = detector.detect(frame)
    if detection is None:
        return VisionResult("sin_deteccion", [], None, now, encode_jpeg(frame))

    reading = classify_light(frame, detection.box, detection.confidence)
    estado = VISUAL_STATES[reading.state]
    annotated = frame.copy()
    x1, y1, x2, y2 = (int(v) for v in detection.box)
    cv2.rectangle(annotated, (x1, y1), (x2, y2), BOX_COLOR, 2)
    cv2.putText(annotated, f"{estado} {detection.confidence:.2f}", (x1, max(y1 - 8, 16)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, BOX_COLOR, 2)
    return VisionResult(estado, [LIGHT_NAMES[l] for l in reading.active], detection.confidence, now,
                        encode_jpeg(annotated))


def encode_jpeg(frame: np.ndarray) -> Optional[bytes]:
    ok, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ok else None


class Monitor:
    """Un solo hilo usa YOLO por turnos: el modelo no se comparte entre hilos y la CPU no se satura."""

    def __init__(self, semaforos: list[dict], detector,
                 interval_seconds: float = SETTINGS["detector"]["inference_interval_seconds"]):
        self.detector = detector
        self.interval_seconds = interval_seconds
        self.feeds = {s["id"]: CameraFeed(s["source"]) for s in semaforos}
        self.results: dict[str, VisionResult] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        for feed in self.feeds.values():
            feed.start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        for feed in self.feeds.values():
            feed.stop()

    def _run(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            for semaforo_id, feed in self.feeds.items():
                try:
                    self.results[semaforo_id] = analyze(feed.read(), self.detector)
                except Exception:  # una camara con error no debe detener a las demas
                    logger.exception("Fallo al analizar la camara %s", semaforo_id)
            self._stop.wait(max(0.0, self.interval_seconds - (time.monotonic() - started)))
