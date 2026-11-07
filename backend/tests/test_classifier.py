import csv
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.classifier import classify_light

BLENDER_DIR = Path(__file__).resolve().parents[2] / "frontend" / "smaforos blender"
COLOR_NAMES = {"rojo": "red", "amarillo": "yellow", "verde": "green"}
BOX = (10, 10, 40, 100)  # zonas de 30 px de alto: y 10-40, 40-70 y 70-100
HOUSING_HSV = (0, 0, 40)


def with_box_hsv(*zones):
    """Frame con una carcasa oscura; zones son (indice de zona, color HSV)."""
    hsv = np.zeros((120, 60, 3), dtype=np.uint8)
    hsv[10:100, 10:40] = HOUSING_HSV
    for zone, color in zones:
        hsv[10 + zone * 30 : 40 + zone * 30, 10:40] = color
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


@pytest.mark.parametrize(
    "zones, state, active",
    [
        ([(0, (4, 60, 255))], "RED", ("red",)),
        ([(0, (175, 60, 255))], "RED", ("red",)),  # el rojo da la vuelta al circulo de tono
        ([(1, (21, 60, 255))], "YELLOW", ("yellow",)),
        ([(2, (63, 25, 255))], "GREEN", ("green",)),
        ([(0, (4, 60, 255)), (2, (63, 25, 255))], "MULTIPLE", ("red", "green")),
        ([], "OFF", ()),
        ([(0, (12, 95, 157))], "OFF", ()),  # carcasa iluminada por el atardecer
        ([(2, (4, 60, 255))], "OFF", ()),  # rojo fuera de su lente: un reflejo, no una luz
    ],
)
def test_states(zones, state, active):
    reading = classify_light(with_box_hsv(*zones), BOX)
    assert (reading.state, reading.active) == (state, active)


@pytest.mark.parametrize(
    "box, confidence",
    [
        (BOX, 0.1),  # confianza por debajo del minimo (0.25)
        ((10, 10, 40, 18), 1.0),  # muy pequena: el tercio no alcanza a leerse
        ((5, 10, 55, 40), 1.0),  # horizontal
        ((70, 130, 90, 180), 1.0),  # fuera del frame
    ],
)
def test_unknown(box, confidence):
    assert classify_light(with_box_hsv(), box, confidence).state == "UNKNOWN"


def blender_rows():
    meta_path = BLENDER_DIR / "meta.csv"
    if not meta_path.exists():
        return []
    with open(meta_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.parametrize("row", blender_rows(), ids=lambda r: f'{r["imagen"]}-{r["escenario"]}')
def test_blender_renders(row):
    # imdecode porque cv2.imread falla con rutas no ASCII en Windows
    image = cv2.imdecode(np.fromfile(BLENDER_DIR / "images" / f'{row["imagen"]}.png', np.uint8), 1)
    height, width = image.shape[:2]
    cx, cy, w, h = (float(row[k]) for k in ("cx", "cy", "w", "h"))
    box = ((cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height)

    expected = {COLOR_NAMES[c] for c in row["luces_encendidas"].split("+") if c}
    assert set(classify_light(image, box).active) == expected
