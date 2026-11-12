import json

import pytest

from app import main
from app.config import ROOT, SETTINGS
from app.ubicacion import MallaVial, normalizar


def via(etiqueta, *puntos):
    return {"type": "Feature", "properties": {"etiqueta": etiqueta},
            "geometry": {"type": "LineString", "coordinates": [list(p) for p in puntos]}}


@pytest.fixture
def malla(tmp_path):
    """Calles de juguete (lng, lat) alrededor de (-74.06, 4.65); 0.0001 grados son unos 11 m."""
    ruta = tmp_path / "malla.geojson"
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": [
        via("AC 72", (-74.07, 4.65), (-74.06, 4.65), (-74.05, 4.65)),
        via("KR 13", (-74.06, 4.64), (-74.06, 4.65), (-74.06, 4.66)),
        via("KR 13 E", (-74.03, 4.64), (-74.03, 4.66)),  # otra via: no es la KR 13
        via("KR 20", (-74.0500, 4.64), (-74.0501, 4.6499)),  # llega a la AC 72 sin compartir vertice
        # Corta la AC 72 dos veces; como en la Malla Vial real, hay un vertice en cada cruce
        via("DG 5", (-74.07, 4.64), (-74.07, 4.65), (-74.07, 4.66), (-74.05, 4.66), (-74.05, 4.65), (-74.05, 4.64)),
    ]}), encoding="utf-8")
    return MallaVial(ruta)


def test_a_crossing_is_found_by_its_two_roads(malla):
    assert malla.cruce("AC 72 con KR 13") == (4.65, -74.06)
    assert malla.cruce("Avenida Calle 72 con Carrera 13") == (4.65, -74.06)  # escrito completo
    assert malla.cruce("CL 72 con KR 13") == (4.65, -74.06)  # en los datos es AC 72


def test_the_equivalent_road_is_tried_when_the_exact_one_does_not_cross(tmp_path):
    ruta = tmp_path / "malla.geojson"
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": [
        via("CL 26", (-74.10, 4.60), (-74.09, 4.60)),  # una CL 26 corta, lejos
        via("AC 26", (-74.07, 4.65), (-74.06, 4.65), (-74.05, 4.65)),  # la avenida, que si cruza
        via("AK 68", (-74.06, 4.64), (-74.06, 4.65), (-74.06, 4.66)),
    ]}), encoding="utf-8")
    assert MallaVial(ruta).cruce("AK 68 con CL 26") == (4.65, -74.06)


def test_a_large_interchange_is_one_crossing(tmp_path):
    ruta = tmp_path / "malla.geojson"
    # Las dos vias se tocan en 3 puntos dentro de unos 100 m (puentes y orejas de un intercambiador)
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": [
        via("AC 26", (-74.070, 4.650), (-74.0600, 4.650), (-74.0595, 4.6503), (-74.0590, 4.650), (-74.05, 4.650)),
        via("AK 68", (-74.060, 4.640), (-74.0600, 4.650), (-74.0595, 4.6503), (-74.0590, 4.650), (-74.059, 4.660)),
    ]}), encoding="utf-8")
    lat, lng = MallaVial(ruta).cruce("AK 68 con AC 26")
    assert abs(lat - 4.6501) < 0.0001 and abs(lng + 74.0595) < 0.0001


def test_roads_that_meet_without_a_shared_vertex_still_cross(malla):
    lat, lng = malla.cruce("AC 72 con KR 20")
    assert abs(lat - 4.65) < 0.0001 and abs(lng + 74.05) < 0.0002


@pytest.mark.parametrize("nombre, mensaje", [
    ("AC 72 y KR 13", "dos vias"),
    ("AC 72 con KR 99", "no aparece"),
    ("KR 13 con KR 13 E", "no se cruzan"),  # paralelas: la E es otra via
    ("AC 72 con DG 5", "en 2 lugares"),
])
def test_unclear_crossings_are_rejected(malla, nombre, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        malla.cruce(nombre)


def test_suffixes_are_kept_apart():
    assert normalizar("Calle 13 Sur") == "CL 13 S"
    assert normalizar("  carrera   13 este ") == "KR 13 E"


def test_hand_written_coordinates_are_kept(malla, tmp_path):
    semaforos = [{"id": "s1", "nombre": "glorieta", "lat": 1.0, "lng": 2.0}]
    assert main.with_positions(semaforos, tmp_path / "no_hace_falta.geojson") == semaforos


def test_the_panel_lights_sit_on_their_real_crossings():
    ruta = ROOT / SETTINGS["road_network"]
    if '"etiqueta"' not in ruta.read_text(encoding="utf-8")[:2000]:
        pytest.skip("La malla vial no trae nombres de vias")
    # Cruces acordados para cada semaforo (revisados uno a uno contra la Malla Vial)
    acordados = {"s1": (4.61444, -74.17479), "s2": (4.67684, -74.14916), "s3": (4.75873, -74.07746),
                 "s4": (4.61847, -74.07494), "s5": (4.57475, -74.12355), "s6": (4.66406, -74.04778),
                 "s7": (4.74648, -74.09617), "s8": (4.70597, -74.11899)}
    assert set(main.SEMAFOROS) == set(acordados)
    for semaforo_id, (lat, lng) in acordados.items():
        calculado = main.SEMAFOROS[semaforo_id]
        distancia_m = max(abs(calculado["lat"] - lat), abs(calculado["lng"] - lng)) * 111_000
        assert distancia_m < 20, (semaforo_id, calculado["nombre"], distancia_m)
