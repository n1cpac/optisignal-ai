# SQLite database management
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional

from app.config import ROOT, SETTINGS
from app.models import EnvioReporte, Opciones, Reporte

DB_PATH = ROOT / SETTINGS["database"]["path"]
MAX_REPORTES = SETTINGS["api"]["max_alerts_per_response"]
ALERT_PREFIX = "[Alerta Automatica Vision]"

# Columnas agregadas despues de la primera version: se crean en bases existentes sin perder datos
ADDED_COLUMNS = {
    "automatica": "INTEGER NOT NULL DEFAULT 0",
    "falla": "INTEGER",
    "comentario": "TEXT",
    "atendida_por": "INTEGER REFERENCES reportes(id)",
    "abierta_en": "TEXT",  # primera vez que un operador abrio la alerta en el panel
    # 1: alerta de una direccion que su semaforo ya no tiene (se movio o se quito): ya no esta pendiente
    "archivada": "INTEGER NOT NULL DEFAULT 0",
    "tipo_falla": "TEXT",
    "semaforos_afectados": "TEXT",
}

# Actuales: alertas del sistema sin atender y de hoy. Historial: cada reporte del operador una sola vez
# (verificado; las alertas que verifico van dentro de el) y las alertas que nadie verifico.
PENDIENTE_HOY = "{t}.automatica = 1 AND {t}.atendida_por IS NULL AND {t}.archivada = 0 AND {t}.fecha >= :hoy"
WHERE_VISTA = {
    # Una fila por semaforo: su alerta pendiente mas reciente (una nueva la reemplaza y la sube)
    "actuales": PENDIENTE_HOY.format(t="r") + " AND r.id = (SELECT max(a.id) FROM reportes a "
                "WHERE a.semaforo_id = r.semaforo_id AND " + PENDIENTE_HOY.format(t="a") + ")",
    "historial": "NOT (" + PENDIENTE_HOY.format(t="r") + ") AND NOT (r.automatica = 1 AND r.atendida_por IS NOT NULL)",
}


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect()) as db, db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS reportes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semaforo_id TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                coincide INTEGER NOT NULL,
                destinatarios TEXT NOT NULL
            )
            """
        )
        existing = {row[1] for row in db.execute("PRAGMA table_info(reportes)")}
        for column, definition in ADDED_COLUMNS.items():
            if column not in existing:
                db.execute(f"ALTER TABLE reportes ADD COLUMN {column} {definition}")
        if "automatica" not in existing:
            # Antes las alertas solo se distinguian por el texto
            db.execute("UPDATE reportes SET automatica = 1 WHERE descripcion LIKE ?", (ALERT_PREFIX + "%",))
        db.execute("CREATE INDEX IF NOT EXISTS idx_reportes_atendida_por ON reportes(atendida_por)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_reportes_automatica_fecha ON reportes(automatica, fecha)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_reportes_semaforo ON reportes(semaforo_id, automatica)")


def insert_reporte(envio: EnvioReporte, ubicacion: str) -> int:
    """Guarda el reporte del operador, lo marca como atencion de las alertas pendientes del semaforo
    y devuelve su id."""
    comentario = envio.comentario.strip()
    prefijo = "Coincide con la imagen" if envio.coincide else "No coincide con la imagen"
    prefijo += ". Fallo en el semaforo" if envio.falla else ". Sin fallo"
    descripcion = f"{prefijo}: {comentario}" if comentario else f"{prefijo}."
    tipo_falla = envio.tipoFalla if envio.falla else None
    semaforos_afectados = json.dumps(envio.semaforosAfectados if envio.falla else [])
    with closing(_connect()) as db, db:
        cursor = db.execute(
            "INSERT INTO reportes (semaforo_id, ubicacion, fecha, descripcion, coincide, destinatarios, "
            "automatica, falla, comentario, tipo_falla, semaforos_afectados) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
            (envio.semaforoId, ubicacion, datetime.now(timezone.utc).isoformat(), descripcion,
             envio.coincide, json.dumps(envio.destinatarios), envio.falla, comentario,
             tipo_falla, semaforos_afectados),
        )
        db.execute(
            "UPDATE reportes SET atendida_por = ? "
            "WHERE semaforo_id = ? AND automatica = 1 AND atendida_por IS NULL AND archivada = 0",
            (cursor.lastrowid, envio.semaforoId),
        )
        return cursor.lastrowid


def archivar_alertas_movidas(direcciones: dict[str, str]) -> int:
    """Archiva las alertas pendientes cuya direccion ya no es la de su semaforo ({id: nombre actual}).

    Los semaforos se identifican por id: si s6 pasa a otro cruce, sus alertas viejas no deben
    seguir en "Actuales" con la direccion anterior ni verificarse con un reporte del lugar nuevo.
    Pasan al historial como no verificadas, con la direccion donde ocurrieron.
    """
    marcadores = ", ".join("?" for _ in direcciones)
    with closing(_connect()) as db, db:
        archivadas = 0
        for semaforo_id, nombre in direcciones.items():
            archivadas += db.execute(
                "UPDATE reportes SET archivada = 1 WHERE automatica = 1 AND atendida_por IS NULL "
                "AND archivada = 0 AND semaforo_id = ? AND ubicacion != ?",
                (semaforo_id, nombre),
            ).rowcount
        archivadas += db.execute(  # semaforos que ya no estan en la configuracion
            "UPDATE reportes SET archivada = 1 WHERE automatica = 1 AND atendida_por IS NULL "
            f"AND archivada = 0 AND semaforo_id NOT IN ({marcadores})",
            tuple(direcciones),
        ).rowcount
    return archivadas


def insert_alerta_sistema(semaforo_id: str, ubicacion: str, tipo_anomalia: str, detalle: str = "") -> int:
    """Registra una alerta confirmada emitida automaticamente por la maquina de estados de vision."""
    descripcion = f"{ALERT_PREFIX} Falla: {tipo_anomalia}."
    if detalle:
        descripcion += f" {detalle}"
    # Cuando enviar una alerta lo decide el monitor (escena nueva o recordatorio)
    with closing(_connect()) as db, db:
        cursor = db.execute(
            "INSERT INTO reportes (semaforo_id, ubicacion, fecha, descripcion, coincide, destinatarios, automatica) "
            "VALUES (?, ?, ?, ?, 0, '[]', 1)",
            (semaforo_id, ubicacion, datetime.now(timezone.utc).isoformat(), descripcion),
        )
        return cursor.lastrowid


def abrir_alerta(alerta_id: int) -> bool:
    """Marca que un operador abrio la alerta en el panel. False si no existe esa alerta."""
    with closing(_connect()) as db, db:
        cursor = db.execute(
            "UPDATE reportes SET abierta_en = COALESCE(abierta_en, ?) WHERE id = ? AND automatica = 1",
            (datetime.now(timezone.utc).isoformat(), alerta_id),
        )
        return cursor.rowcount == 1


def alerta_vista(alerta_id: int) -> bool:
    """Un operador ya la abrio o la atendio con un reporte."""
    with closing(_connect()) as db:
        row = db.execute(
            "SELECT abierta_en IS NOT NULL OR atendida_por IS NOT NULL FROM reportes WHERE id = ?", (alerta_id,)
        ).fetchone()
    return bool(row and row[0])


def semaforo_de_reporte(reporte_id: int) -> Optional[str]:
    """Devuelve el semaforo_id al que pertenece un reporte o alerta, o None si no existe."""
    try:
        with closing(_connect()) as db:
            row = db.execute("SELECT semaforo_id FROM reportes WHERE id = ?", (reporte_id,)).fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None


def semaforo_atendido_hoy(semaforo_id: str, hoy: Optional[str] = None) -> bool:
    """True si el operador ya registro un reporte hoy para este semaforo."""
    try:
        with closing(_connect()) as db:
            row = db.execute(
                "SELECT 1 FROM reportes WHERE semaforo_id = ? AND automatica = 0 AND fecha >= ? LIMIT 1",
                (semaforo_id, hoy or inicio_de_hoy()),
            ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False


def reset_reportes() -> None:
    """Limpia todos los reportes y alertas para reiniciar la demostracion."""
    with closing(_connect()) as db, db:
        db.execute("DELETE FROM reportes")


def _opciones(
    id_,
    fecha,
    coincide,
    falla,
    destinatarios,
    comentario,
    tipo_falla=None,
    semaforos_afectados=None,
) -> Optional[Opciones]:
    if id_ is None:
        return None
    return Opciones(
        reporteId=str(id_),
        fecha=fecha,
        coincide=bool(coincide),
        falla=None if falla is None else bool(falla),
        destinatarios=json.loads(destinatarios),
        comentario=comentario,
        tipoFalla=tipo_falla,
        semaforosAfectados=json.loads(semaforos_afectados) if semaforos_afectados else [],
    )


def inicio_de_hoy() -> str:
    """Medianoche local en UTC ISO: las alertas de antes pasan al historial al cambiar el dia del calendario."""
    medianoche = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return medianoche.astimezone(timezone.utc).isoformat()


def list_reportes(vista: str, pagina: int = 1, tamano: int = MAX_REPORTES,
                  hoy: Optional[str] = None) -> tuple[list[Reporte], int, Optional[int]]:
    """Una pagina de la vista ("actuales" o "historial"), mas recientes primero, el total de la vista
    y el id mas reciente de toda la vista (el panel lo usa para saber si llego una alerta nueva)."""
    where = WHERE_VISTA[vista]
    params = {"hoy": hoy or inicio_de_hoy(), "limite": tamano, "desde": (pagina - 1) * tamano}
    # Cada fila trae sus opciones: las propias si es del operador, o las del reporte que atendio la alerta
    with closing(_connect()) as db:
        total, ultimo_id = db.execute(f"SELECT count(*), max(r.id) FROM reportes r WHERE {where}", params).fetchone()
        rows = db.execute(
            f"""
            SELECT r.id, r.semaforo_id, r.ubicacion, r.fecha, r.descripcion, r.automatica,
                   (SELECT count(*) FROM reportes a WHERE a.atendida_por = r.id),
                   (SELECT a.descripcion FROM reportes a WHERE a.atendida_por = r.id ORDER BY a.id DESC LIMIT 1),
                   o.id, o.fecha, o.coincide, o.falla, o.destinatarios, o.comentario,
                   o.tipo_falla, o.semaforos_afectados
            FROM reportes r
            LEFT JOIN reportes o ON o.id = CASE WHEN r.automatica = 1 THEN r.atendida_por ELSE r.id END
            WHERE {where}
            ORDER BY r.id DESC LIMIT :limite OFFSET :desde
            """,
            params,
        ).fetchall()
    reportes = [
        Reporte(id=str(id_), semaforoId=semaforo_id, ubicacion=ubicacion, fecha=fecha, descripcion=descripcion,
                automatica=bool(automatica), alertasVerificadas=verificadas, ultimaAlertaVerificada=ultima,
                opciones=_opciones(*opciones))
        for id_, semaforo_id, ubicacion, fecha, descripcion, automatica, verificadas, ultima, *opciones in rows
    ]
    return reportes, total, ultimo_id
