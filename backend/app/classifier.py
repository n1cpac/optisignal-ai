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
    if zone_hsv.size == 0:
        return 0.0
    lower_s, lower_v = color["saturation_min"], color["brightness_min"]
    mask = np.zeros(zone_hsv.shape[:2], dtype=np.uint8)
    for hue_min, hue_max in color["hue_ranges"]:
        lower = np.array([hue_min, lower_s, lower_v], dtype=np.uint8)
        upper = np.array([hue_max, 255, 255], dtype=np.uint8)
        mask |= cv2.inRange(zone_hsv, lower, upper)

    total_pixels = float(mask.size)
    color_hits = float(np.count_nonzero(mask))
    base_ratio = color_hits / total_pixels

    # Si existe una corona cromatica clara del color del lente, incluir el nucleo LED
    # saturado en blanco (bloom nocturno / sobreexposicion en s1 y s5) dentro del mismo tercio
    if base_ratio >= 0.035:
        white_core = cv2.inRange(
            zone_hsv,
            np.array([0, 0, 238], dtype=np.uint8),
            np.array([179, 32, 255], dtype=np.uint8),
        )
        combined = cv2.bitwise_or(mask, white_core)
        color_hits = float(np.count_nonzero(combined))

    # Descartar pixeles de cielo azul/celeste y nubes blancas/grises brillantes alrededor de la carcasa
    blue_sky = cv2.inRange(
        zone_hsv,
        np.array([92, 12, 140], dtype=np.uint8),
        np.array([142, 255, 255], dtype=np.uint8),
    )
    overcast_sky = cv2.inRange(
        zone_hsv,
        np.array([0, 0, 160], dtype=np.uint8),
        np.array([179, 23, 237], dtype=np.uint8),
    )
    sky_mask = cv2.bitwise_or(blue_sky, overcast_sky)
    sky_pixels = float(np.count_nonzero(sky_mask))
    effective_area = max(total_pixels * 0.25, total_pixels - sky_pixels)
    return min(1.0, color_hits / effective_area)


def _filter_halo_bleed(active: tuple[str, ...], ratios: dict[str, float]) -> tuple[str, ...]:
    """Distingue encendido simultaneo real (MULTIPLE) del sangrado optico (bloom) hacia un lente vecino."""
    if len(active) <= 1:
        return active
    primary_lens = max(active, key=lambda l: ratios[l])
    primary_ratio = ratios[primary_lens]
    if primary_ratio <= 0.0:
        return active

    # Mantener solo los lentes cuya activacion sea comparable al dominante (>= 48%)
    filtered = tuple(
        lens for lens in active
        if lens == primary_lens or ratios[lens] >= 0.48 * primary_ratio
    )
    return filtered if filtered else (primary_lens,)


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

    # Concentrar el analisis en la columna optica central (75% central del ancho)
    # descartando postes de soporte amarillos y viseras en los laterales
    x_margin = int(roi_width * 0.125) if roi_width >= 16 else 0
    roi_center = roi[:, x_margin : roi_width - x_margin] if x_margin > 0 else roi

    hsv = cv2.cvtColor(roi_center, cv2.COLOR_BGR2HSV)
    center_height = roi_center.shape[0]
    ratios = {
        lens: _lens_ratio(
            hsv[i * center_height // 3 : (i + 1) * center_height // 3], config["colors"][lens]
        )
        for i, lens in enumerate(LENSES)
    }
    raw_active = tuple(lens for lens in LENSES if ratios[lens] >= config["activation_threshold"])
    active = _filter_halo_bleed(raw_active, ratios)

    if not active:
        state = "OFF"
    elif len(active) == 1:
        state = active[0].upper()
    else:
        state = "MULTIPLE"
    return LightReading(state, active, ratios)
