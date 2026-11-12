# YOLO detector module con soporte para ensamble de modelos y consenso de criterios
from typing import List, NamedTuple, Optional

import numpy as np
from ultralytics import YOLO

from app.config import ROOT, SETTINGS


class Detection(NamedTuple):
    box: tuple[float, float, float, float]  # xyxy en pixeles
    confidence: float
    sources: int = 1


def box_iou(b1: tuple[float, float, float, float], b2: tuple[float, float, float, float]) -> float:
    """Calcula la intersección sobre unión (IoU) entre dos bounding boxes en formato xyxy."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0.0 else 0.0


class Detector:
    def __init__(self, settings: dict = SETTINGS["detector"]):
        self.settings = settings
        
        # Determinar si se usa ensamble o un único modelo
        use_ensemble = settings.get("ensemble", True)
        if use_ensemble and "model_paths" in settings:
            paths = settings["model_paths"]
        elif "model_paths" in settings and not settings.get("model_path"):
            paths = settings["model_paths"]
        else:
            paths = [settings.get("model_path", "models/blender_best.pt")]

        self.models = [YOLO(str(ROOT / p)) for p in paths]
        # Compatibilidad hacia atrás: self.model apunta al modelo principal
        self.model = self.models[0]

    def detect(self, frame: Optional[np.ndarray]) -> Optional[Detection]:
        if frame is None:
            return None

        conf_thresh = self.settings.get("confidence_threshold", 0.25)
        iou_thresh = self.settings.get("iou_threshold", 0.45)
        imgsz = self.settings.get("input_size", 640)
        device = self.settings.get("device", "cpu")

        all_candidates: List[Detection] = []
        for model in self.models:
            result = model.predict(
                frame,
                conf=conf_thresh,
                iou=iou_thresh,
                imgsz=imgsz,
                device=device,
                verbose=False,
            )[0]
            for box, confidence in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
                if box[3] - box[1] > box[2] - box[0]:  # el clasificador solo lee semaforos verticales
                    all_candidates.append(Detection(tuple(box), confidence, 1))

        if not all_candidates:
            return None

        # Si solo hay 1 modelo cargado, retornar el de mayor confianza directamente
        if len(self.models) == 1:
            return max(all_candidates, key=lambda d: d.confidence, default=None)

        # Agrupar detecciones superpuestas de diferentes modelos (consenso de criterio)
        clusters: List[List[Detection]] = []
        for det in sorted(all_candidates, key=lambda d: d.confidence, reverse=True):
            matched = False
            for cluster in clusters:
                if box_iou(det.box, cluster[0].box) >= 0.40:
                    cluster.append(det)
                    matched = True
                    break
            if not matched:
                clusters.append([det])

        fused_detections: List[Detection] = []
        for cluster in clusters:
            weights = [d.confidence for d in cluster]
            total_weight = sum(weights)
            # Promedio ponderado de las coordenadas por la confianza de cada modelo
            avg_box = (
                sum(d.box[0] * w for d, w in zip(cluster, weights)) / total_weight,
                sum(d.box[1] * w for d, w in zip(cluster, weights)) / total_weight,
                sum(d.box[2] * w for d, w in zip(cluster, weights)) / total_weight,
                sum(d.box[3] * w for d, w in zip(cluster, weights)) / total_weight,
            )
            # Bonificación de confianza si varios modelos coinciden en el mismo semáforo
            base_conf = max(d.confidence for d in cluster)
            boost = 0.05 * (len(cluster) - 1)
            fused_conf = min(1.0, base_conf + boost)
            fused_detections.append(Detection(avg_box, fused_conf, len(cluster)))

        # Criterio de decisión: priorizar consenso (más modelos que lo avalan), luego confianza
        return max(fused_detections, key=lambda d: (d.sources, d.confidence), default=None)
