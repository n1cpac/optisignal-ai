# HSV color classifier module
from typing import NamedTuple, Sequence

import cv2
import numpy as np

from app.config import SETTINGS

# Orden de los lentes de arriba hacia abajo: cada color se busca solo en su tercio de la ROI.
LENSES = ("red", "yellow", "green")


class LightReading(NamedTuple):
    state: str  # RED, YELLOW, GREEN, MULTIPLE, OFF o UNKNOWN
    active: tuple[str, ...]  # lentes encendidos, de arriba hacia abajo
    ratios: dict[str, float]  # fraccion de pixeles encendidos en la zona de cada lente


CONFIG = {
    "colors": {lens: SETTINGS["color_classification"][lens] for lens in LENSES},
    "activation_threshold": SETTINGS["color_classification"]["activation_threshold"],
    "min_roi_height": SETTINGS["color_classification"]["min_roi_height"],
    "confidence_threshold": SETTINGS["detector"]["confidence_threshold"],
}


def _lens_ratio(zone_hsv: np.ndarray, color: dict) -> float:
    lower_s, lower_v = color["saturation_min"], color["brightness_min"]
    mask = np.zeros(zone_hsv.shape[:2], dtype=np.uint8)
    for hue_min, hue_max in color["hue_ranges"]:
        lower = np.array([hue_min, lower_s, lower_v], dtype=np.uint8)
        upper = np.array([hue_max, 255, 255], dtype=np.uint8)
        mask |= cv2.inRange(zone_hsv, lower, upper)
    return float(np.count_nonzero(mask)) / mask.size


def classify_light(
    frame: np.ndarray,
    box: Sequence[float],
    confidence: float = 1.0,
    config: dict = CONFIG,
) -> LightReading:
    """Clasifica las luces de un semaforo a partir de un frame BGR y una caja xyxy en pixeles."""
    unknown = LightReading("UNKNOWN", (), {})
    if confidence < config["confidence_threshold"]:
        return unknown

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(round(float(v))) for v in box)
    roi = frame[max(y1, 0) : min(y2, height), max(x1, 0) : min(x2, width)]
    roi_height, roi_width = roi.shape[:2]

    # shortcut: un semaforo horizontal (ancho >= alto) da UNKNOWN, soportarlo si aparecen camaras con ellos
    if roi_height < config["min_roi_height"] or roi_width >= roi_height:
        return unknown

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    ratios = {
        lens: _lens_ratio(
            hsv[i * roi_height // 3 : (i + 1) * roi_height // 3], config["colors"][lens]
        )
        for i, lens in enumerate(LENSES)
    }
    active = tuple(lens for lens in LENSES if ratios[lens] >= config["activation_threshold"])

    if not active:
        state = "OFF"
    elif len(active) == 1:
        state = active[0].upper()
    else:
        state = "MULTIPLE"
    return LightReading(state, active, ratios)
