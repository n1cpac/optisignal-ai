# YOLO detector module
from typing import NamedTuple, Optional

import numpy as np
from ultralytics import YOLO

from app.config import ROOT, SETTINGS


class Detection(NamedTuple):
    box: tuple[float, float, float, float]  # xyxy en pixeles
    confidence: float


class Detector:
    def __init__(self, settings: dict = SETTINGS["detector"]):
        self.settings = settings
        self.model = YOLO(str(ROOT / settings["model_path"]))

    def detect(self, frame: np.ndarray) -> Optional[Detection]:
        result = self.model.predict(
            frame,
            conf=self.settings["confidence_threshold"],
            iou=self.settings["iou_threshold"],
            imgsz=self.settings["input_size"],
            device=self.settings["device"],
            verbose=False,
        )[0]
        boxes = [
            Detection(tuple(box), confidence)
            for box, confidence in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist())
            if box[3] - box[1] > box[2] - box[0]  # el clasificador solo lee semaforos verticales
        ]
        # shortcut: asume un semaforo por camara, usar la zona esperada de cada camara si se confunde
        return max(boxes, key=lambda d: d.confidence, default=None)
