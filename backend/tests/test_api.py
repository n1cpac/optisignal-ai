import pytest
from fastapi.testclient import TestClient

from app import database, main
from app.config import SETTINGS
from app.detector import Detection


class StubDetector:
    def detect(self, frame):
        return Detection((0.0, 0.0, 10.0, 40.0), 0.9)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(main, "Detector", StubDetector)
    # Las pruebas no deben abrir la camara real (OBS) aunque la configuracion la use
    monkeypatch.setitem(main.SEMAFOROS, "s1", {**main.SEMAFOROS["s1"], "source": "data/test_videos/test1.mp4"})
    with TestClient(main.app) as test_client:
        yield test_client


def envio(**overrides):
    return {"semaforoId": "s1", "coincide": False, "falla": True, "comentario": " sin luz ",
            "destinatarios": ["tecnicos"], **overrides}


def test_semaforos_follow_the_panel_contract(client):
    semaforos = client.get("/semaforos").json()
    assert [s["id"] for s in semaforos] == [s["id"] for s in SETTINGS["semaforos"]]
    assert semaforos[0]["imagenUrl"] == "/camaras/s1/mjpeg"
    assert semaforos[0]["fuenteImagen"] == "url"
    assert semaforos[0]["estadoElectrico"] == "rojo"
    assert semaforos[0]["lucesElectricas"] == ["rojo"]
    assert "estadoVisual" in semaforos[0]


def test_only_s1_is_a_camera_and_the_rest_get_distinct_renders():
    sources = [s["source"] for s in main.SEMAFOROS.values()]
    assert sources[0] == SETTINGS["semaforos"][0]["source"]
    assert all(s.endswith(".png") and "renders_escenarios" in s for s in sources[1:])
    assert len(set(sources[1:])) == len(sources) - 1  # sin renders repetidos


def make_renders(folder, *names):
    folder.mkdir()
    for name in names:
        (folder / name).touch()
    return str(folder)


def test_render_name_sets_the_electrical_state(tmp_path):
    folder = make_renders(tmp_path / "renders", "rojo_01_dia_rojo.png", "apagado_02_noche_ninguna.png",
                          "dos_luces_03_dia_rojo+verde.png")
    camera = {"id": "s1", "source": 0, "electrico": "rojo"}
    semaforos = main.with_random_renders(
        [camera] + [{"id": f"s{i}", "source": folder} for i in (2, 3, 4)], main.random.Random(0))

    assert semaforos[0] is camera
    states = {(s["electrico"], tuple(s["luces_electricas"]), s["falla"]) for s in semaforos[1:]}
    assert states == {("rojo", ("rojo",), False), ("apagado", (), True), ("multiple", ("rojo", "verde"), True)}


@pytest.mark.parametrize(
    "names, count",
    [(["rojo_01_dia_rojo.png"], 2), (["raro_01_dia_azul.png"], 1)],
    ids=["faltan renders", "nombre desconocido"],
)
def test_bad_render_folders_fail_at_startup(tmp_path, names, count):
    folder = make_renders(tmp_path / "renders", *names)
    with pytest.raises(ValueError):
        main.with_random_renders([{"id": f"s{i}", "source": folder} for i in range(count)])


def test_report_is_saved_and_listed_newest_first(client):
    ids = [client.post("/reportes/envio", json=cuerpo).json()["id"] for cuerpo in (
        envio(),
        envio(coincide=True, falla=False, comentario="", destinatarios=[]),
        envio(destinatarios=[]),  # fallo sin avisar a nadie
    )]

    pagina = client.get("/reportes", params={"vista": "historial"}).json()
    reportes = pagina["items"]
    assert (pagina["total"], pagina["pagina"], client.get("/reportes").json()["total"]) == (3, 1, 0)
    assert [r["id"] for r in reportes] == ids[::-1]  # la respuesta trae el id de cada reporte
    assert [r["descripcion"] for r in reportes] == [
        "No coincide con la imagen. Fallo en el semaforo: sin luz",
        "Coincide con la imagen. Sin fallo.",
        "No coincide con la imagen. Fallo en el semaforo: sin luz",
    ]
    assert reportes[0]["ubicacion"] == main.SEMAFOROS["s1"]["nombre"]


@pytest.mark.parametrize(
    "overrides, status",
    [
        ({"semaforoId": "nope"}, 404),
        ({"falla": False}, 422),  # destinatarios solo con fallo
        ({"falla": None}, 422),
        ({"destinatarios": ["alcalde"]}, 422),
        ({"comentario": "x" * 2001}, 422),
    ],
)
def test_invalid_reports_are_rejected(client, overrides, status):
    assert client.post("/reportes/envio", json=envio(**overrides)).status_code == status
    assert client.get("/reportes", params={"vista": "historial"}).json()["total"] == 0


@pytest.mark.parametrize("params", [{"vista": "todo"}, {"pagina": 0}, {"tamano": 0}, {"tamano": 1000}])
def test_invalid_pages_are_rejected(client, params):
    assert client.get("/reportes", params=params).status_code == 422


def test_opening_an_alert(client):
    alerta_id = database.insert_alerta_sistema("s1", "AC 13 con CL 13", "ALL_LIGHTS_OFF")
    assert client.get("/reportes").json()["ultimoId"] == alerta_id
    assert client.post(f"/reportes/{alerta_id}/abrir").json() == {"ok": True}
    assert database.alerta_vista(alerta_id)

    client.post("/reportes/envio", json=envio())
    reporte_id = client.get("/reportes", params={"vista": "historial"}).json()["items"][0]["opciones"]["reporteId"]
    assert client.post(f"/reportes/{reporte_id}/abrir").status_code == 404  # no es una alerta
    assert client.post("/reportes/9999/abrir").status_code == 404


def test_unknown_camera_is_not_found(client):
    assert client.get("/camaras/nope/mjpeg").status_code == 404


def test_history_reports_get_a_fixed_random_scene(client):
    primera = client.get("/reportes/7/escena")
    assert (primera.status_code, primera.headers["content-type"]) == (200, "image/png")
    assert primera.content.startswith(b"\x89PNG")
    assert client.get("/reportes/7/escena").content == primera.content  # siempre la misma para el mismo reporte
    escenas = {client.get(f"/reportes/{i}/escena").content for i in range(1, 30)}
    assert len(escenas) > 1  # distintos reportes reciben escenas distintas
