# Ciclo de vision: lee cada camara, detecta con YOLO, clasifica en HSV y audita con FSM
import logging
import threading
import time
from datetime import datetime, timezone
from typing import NamedTuple, Optional

import cv2
import numpy as np

from app import database
from app.camera import CameraFeed
from app.classifier import classify_light
from app.config import SETTINGS
from app.detector import Detection
from app.state_machine import TrafficLightFSM

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
NORMAL_BOX_COLOR = (255, 111, 30)   # Naranja OptiSignal
ANOMALY_BOX_COLOR = (0, 0, 255)     # Rojo BGR para alerta de anomalia confirmada


class VisionResult(NamedTuple):
    estado_visual: str
    luces: list[str]
    confianza: Optional[float]
    actualizado: str  # ISO 8601
    jpeg: Optional[bytes]  # frame anotado; None mientras no haya senal
    anomalia_confirmada: Optional[str] = None
    tiempo_en_estado: float = 0.0


def analyze(frame: Optional[np.ndarray], detector, fsm: Optional[TrafficLightFSM] = None) -> VisionResult:
    now = datetime.now(timezone.utc).isoformat()
    if frame is None:
        if fsm:
            fsm.update("UNKNOWN")
        return VisionResult("sin_senal", [], None, now, None, None, 0.0)

    detection: Optional[Detection] = detector.detect(frame)
    if detection is None:
        fsm_status = fsm.update("UNKNOWN") if fsm else None
        anomalia = fsm_status.confirmed_anomaly if fsm_status else None
        tiempo = fsm_status.time_in_state if fsm_status else 0.0
        return VisionResult("sin_deteccion", [], None, now, encode_jpeg(frame), anomalia, tiempo)

    reading = classify_light(frame, detection.box, detection.confidence)
    estado = VISUAL_STATES[reading.state]

    # Actualizar la maquina de estados finitos (FSM)
    fsm_status = fsm.update(reading.state) if fsm else None
    confirmed_anomaly = fsm_status.confirmed_anomaly if fsm_status else None
    time_in_state = fsm_status.time_in_state if fsm_status else 0.0

    # Dibujar anotaciones visuales
    annotated = frame.copy()
    x1, y1, x2, y2 = (int(v) for v in detection.box)
    box_color = ANOMALY_BOX_COLOR if confirmed_anomaly else NORMAL_BOX_COLOR

    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
    label = f"{estado} {detection.confidence:.2f}"
    if confirmed_anomaly:
        label += f" [{confirmed_anomaly}]"

    cv2.putText(annotated, label, (x1, max(y1 - 8, 16)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

    return VisionResult(
        estado_visual=estado,
        luces=[LIGHT_NAMES[l] for l in reading.active],
        confianza=detection.confidence,
        actualizado=now,
        jpeg=encode_jpeg(annotated),
        anomalia_confirmada=confirmed_anomaly,
        tiempo_en_estado=time_in_state,
    )


def encode_jpeg(frame: np.ndarray) -> Optional[bytes]:
    ok, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ok else None


class Monitor:
    """Un solo hilo usa YOLO por turnos y audita la coherencia temporal de cada camara con su propia FSM."""

    def __init__(self, semaforos: list[dict], detector,
                 interval_seconds: float = SETTINGS["detector"]["inference_interval_seconds"]):
        self.detector = detector
        self.interval_seconds = interval_seconds
        self.semaforos_config = {s["id"]: s for s in semaforos}
        self.feeds = {s["id"]: CameraFeed(s["source"]) for s in semaforos}
        self.fsms = {s["id"]: TrafficLightFSM() for s in semaforos}
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
                    fsm = self.fsms[semaforo_id]
                    result = analyze(feed.read(), self.detector, fsm)
                    self.results[semaforo_id] = result

                    # Si la FSM confirma una anomalia, persistir automaticamente en base de datos
                    if result.anomalia_confirmada:
                        ubicacion = self.semaforos_config[semaforo_id].get("nombre", semaforo_id)
                        database.insert_alerta_sistema(
                            semaforo_id=semaforo_id,
                            ubicacion=ubicacion,
                            tipo_anomalia=result.anomalia_confirmada,
                            detalle=f"Estado visual: {result.estado_visual}. Luces: {', '.join(result.luces) or 'ninguna'}"
                        )
                except Exception:
                    logger.exception("Fallo al analizar la camara %s", semaforo_id)
            self._stop.wait(max(0.0, self.interval_seconds - (time.monotonic() - started)))
