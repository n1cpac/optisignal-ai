import sqlite3

import pytest

from app import database
from app.models import EnvioReporte

HOY = "2026-11-07T05:00:00+00:00"  # medianoche en Bogota
AYER = "2026-11-06T15:00:00+00:00"
HOY_MAS_TARDE = "2026-11-07T20:00:00+00:00"


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init()


def envio(semaforo_id="s1", **overrides):
    return EnvioReporte(**{"semaforoId": semaforo_id, "coincide": False, "falla": True,
                           "comentario": " sin luz ", "destinatarios": ["tecnicos"], **overrides})


def alerta(semaforo_id="s1", fecha=HOY_MAS_TARDE):
    alerta_id = database.insert_alerta_sistema(semaforo_id, "AC 13", "ALL_LIGHTS_OFF")
    with sqlite3.connect(database.DB_PATH) as conn:
        conn.execute("UPDATE reportes SET fecha = ? WHERE id = ?", (fecha, alerta_id))
    return alerta_id


def vista(nombre, **kwargs):
    return database.list_reportes(nombre, hoy=HOY, **kwargs)[0]


def test_today_unattended_alerts_are_current_and_the_rest_is_history(db):
    alerta("s1")
    alerta("s2", fecha=AYER)  # cambio el dia del calendario sin atenderse
    alerta("s3")
    database.insert_reporte(envio("s3"), "AK 7")  # atiende la de s3
    database.insert_reporte(envio("s4"), "AC 145")  # reporte sin alerta previa

    assert [r.semaforoId for r in vista("actuales")] == ["s1"]
    historial = {r.semaforoId: r for r in vista("historial")}
    assert set(historial) == {"s2", "s3", "s4"}  # la alerta de s3 va dentro de su reporte, no aparte
    assert (historial["s2"].automatica, historial["s2"].opciones) == (True, None)  # no verificada
    assert (historial["s3"].automatica, historial["s3"].alertasVerificadas) == (False, 1)
    assert historial["s3"].opciones.comentario == "sin luz"
    assert (historial["s4"].alertasVerificadas, historial["s4"].opciones.reporteId) == (0, historial["s4"].id)


def test_a_report_attends_the_pending_alerts_of_its_traffic_light_only(db):
    alerta("s1")
    alerta("s2")
    database.insert_reporte(envio("s1"), "AC 13")

    assert [r.semaforoId for r in vista("actuales")] == ["s2"]
    [reporte] = vista("historial")  # una sola entrada: el reporte, con la alerta que verifico
    assert (reporte.semaforoId, reporte.automatica, reporte.alertasVerificadas) == ("s1", False, 1)
    assert reporte.ultimaAlertaVerificada.startswith("[Alerta Automatica Vision] Falla: ALL_LIGHTS_OFF")
    o = reporte.opciones
    assert (o.coincide, o.falla, o.destinatarios, o.comentario) == (False, True, ["tecnicos"], "sin luz")


def test_an_attended_alert_keeps_the_report_that_attended_it(db):
    alerta("s1")
    database.insert_reporte(envio(coincide=True), "AC 13")
    database.insert_reporte(envio(comentario="segundo"), "AC 13")

    segundo, primero = vista("historial")
    assert (primero.opciones.coincide, primero.alertasVerificadas) == (True, 1)  # la verifico el primero
    assert segundo.alertasVerificadas == 0


def test_pages_are_newest_first_and_report_the_total(db):
    ids = [alerta(f"s{i}") for i in range(5)]
    pagina_1, total, ultimo_id = database.list_reportes("actuales", 1, 2, hoy=HOY)
    pagina_3, _, _ = database.list_reportes("actuales", 3, 2, hoy=HOY)
    assert (total, ultimo_id) == (5, ids[4])
    assert [r.id for r in pagina_1] == [str(ids[4]), str(ids[3])]
    assert [r.id for r in pagina_3] == [str(ids[0])]
    assert database.list_reportes("actuales", 4, 2, hoy=HOY) == ([], 5, ids[4])


def test_current_alerts_show_each_traffic_light_once_with_its_newest_alert_first(db):
    primera_s1 = alerta("s1")
    alerta("s2")
    nueva_s1 = alerta("s1")  # otra alerta de la misma camara: reemplaza su fila y la sube

    actuales, total, ultimo_id = database.list_reportes("actuales", hoy=HOY)
    assert [(r.semaforoId, r.id) for r in actuales] == [("s1", str(nueva_s1)), ("s2", actuales[1].id)]
    assert (total, ultimo_id) == (2, nueva_s1)
    assert str(primera_s1) not in {r.id for r in vista("historial")}  # sigue pendiente: ni aparte ni en historial

    reporte_id = database.insert_reporte(envio("s1"), "AC 13")  # atender la fila atiende todas las de esa camara
    assert [r.semaforoId for r in vista("actuales")] == ["s2"]
    [reporte] = vista("historial")  # una entrada por reporte, no una por alerta verificada
    assert (reporte.id, reporte.alertasVerificadas) == (str(reporte_id), 2)


def test_an_alert_counts_as_seen_when_opened_or_attended(db):
    abierta, atendida, pendiente = alerta("s1"), alerta("s2"), alerta("s3")
    assert database.abrir_alerta(abierta)
    database.insert_reporte(envio("s2"), "AC 72")

    assert [database.alerta_vista(a) for a in (abierta, atendida, pendiente)] == [True, True, False]
    assert not database.abrir_alerta(9999)


def test_old_databases_gain_the_new_columns_without_losing_rows(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as old:
        old.execute("CREATE TABLE reportes (id INTEGER PRIMARY KEY AUTOINCREMENT, semaforo_id TEXT NOT NULL, "
                    "ubicacion TEXT NOT NULL, fecha TEXT NOT NULL, descripcion TEXT NOT NULL, "
                    "coincide INTEGER NOT NULL, destinatarios TEXT NOT NULL)")
        old.execute("INSERT INTO reportes VALUES (1, 's1', 'AC 13', '2026-11-05T20:00:00+00:00', "
                    "'Coincide con la imagen: todo bien', 1, '[\"transito\"]')")
        old.execute("INSERT INTO reportes VALUES (2, 's5', 'AC 63', '2026-11-06T20:00:00+00:00', "
                    "'[Alerta Automatica Vision] Falla: MULTIPLE_LIGHTS_ON.', 0, '[\"tecnicos\", \"transito\"]')")
    old.close()
    monkeypatch.setattr(database, "DB_PATH", path)

    database.init()
    database.init()  # una segunda vez no debe fallar ni repetir nada

    alerta_vieja, reporte = vista("historial")
    assert (alerta_vieja.automatica, alerta_vieja.opciones) == (True, None)
    assert (reporte.automatica, reporte.opciones.coincide, reporte.opciones.falla,
            reporte.opciones.comentario) == (False, True, None, None)


def test_alerts_from_a_previous_address_leave_current_alerts(db):
    vieja = alerta("s6")  # s6 estaba en otro cruce
    with sqlite3.connect(database.DB_PATH) as conn:
        conn.execute("UPDATE reportes SET ubicacion = 'AK 97 con CL 16I' WHERE id = ?", (vieja,))
    de_un_semaforo_quitado = alerta("s9")
    actual = alerta("s1")  # su ubicacion es "AC 13", la direccion vigente de s1

    assert database.archivar_alertas_movidas({"s1": "AC 13", "s6": "AK 7 con CL 84"}) == 2
    assert database.archivar_alertas_movidas({"s1": "AC 13", "s6": "AK 7 con CL 84"}) == 0  # ya archivadas

    assert [r.id for r in vista("actuales")] == [str(actual)]
    historial = {r.id: r for r in vista("historial")}
    assert {str(vieja), str(de_un_semaforo_quitado)} <= set(historial)  # no verificadas, con su direccion
    assert historial[str(vieja)].ubicacion == "AK 97 con CL 16I"

    database.insert_reporte(envio("s6"), "AK 7 con CL 84")  # un reporte del lugar nuevo
    assert database.alerta_vista(vieja) is False  # no verifica la alerta del lugar anterior
