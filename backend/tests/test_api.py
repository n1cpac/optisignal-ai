import pytest
from fastapi.testclient import TestClient

from app import database, main
from app.detector import Detection


class StubDetector:
    def detect(self, frame):
        return Detection((0.0, 0.0, 10.0, 40.0), 0.9)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(main, "Detector", StubDetector)
    with TestClient(main.app) as test_client:
        yield test_client


def envio(**overrides):
    return {"semaforoId": "s1", "coincide": False, "comentario": " sin luz ",
            "destinatarios": ["tecnicos"], **overrides}


def test_semaforos_follow_the_panel_contract(client):
    semaforos = client.get("/semaforos").json()
    assert [s["id"] for s in semaforos] == [f"s{i}" for i in range(1, 9)]
    assert semaforos[0]["imagenUrl"] == "/camaras/s1/mjpeg"
    assert semaforos[0]["fuenteImagen"] == "url"
    assert semaforos[0]["estadoElectrico"] == "rojo"
    assert "estadoVisual" in semaforos[0]


def test_report_is_saved_and_listed_newest_first(client):
    assert client.post("/reportes/envio", json=envio()).json() == {"ok": True}
    assert client.post("/reportes/envio", json=envio(coincide=True, comentario="")).json() == {"ok": True}

    reportes = client.get("/reportes").json()
    assert [r["descripcion"] for r in reportes] == [
        "Coincide con la imagen.",
        "No coincide con la imagen: sin luz",
    ]
    assert reportes[0]["ubicacion"] == "AC 13 con CL 13"


@pytest.mark.parametrize(
    "overrides, status",
    [
        ({"semaforoId": "nope"}, 404),
        ({"destinatarios": []}, 422),
        ({"destinatarios": ["alcalde"]}, 422),
        ({"comentario": "x" * 2001}, 422),
    ],
)
def test_invalid_reports_are_rejected(client, overrides, status):
    assert client.post("/reportes/envio", json=envio(**overrides)).status_code == status
    assert client.get("/reportes").json() == []


def test_unknown_camera_is_not_found(client):
    assert client.get("/camaras/nope/mjpeg").status_code == 404
