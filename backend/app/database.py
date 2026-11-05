# SQLite database management
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from app.config import ROOT, SETTINGS
from app.models import EnvioReporte, Reporte

DB_PATH = ROOT / SETTINGS["database"]["path"]
MAX_REPORTES = SETTINGS["api"]["max_alerts_per_response"]


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


def insert_reporte(envio: EnvioReporte, ubicacion: str) -> None:
    prefijo = "Coincide con la imagen" if envio.coincide else "No coincide con la imagen"
    descripcion = f"{prefijo}: {envio.comentario.strip()}" if envio.comentario.strip() else f"{prefijo}."
    with closing(_connect()) as db, db:
        db.execute(
            "INSERT INTO reportes (semaforo_id, ubicacion, fecha, descripcion, coincide, destinatarios) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (envio.semaforoId, ubicacion, datetime.now(timezone.utc).isoformat(), descripcion,
             envio.coincide, json.dumps(envio.destinatarios)),
        )


def list_reportes() -> list[Reporte]:
    with closing(_connect()) as db:
        rows = db.execute(
            "SELECT id, semaforo_id, ubicacion, fecha, descripcion FROM reportes "
            "ORDER BY id DESC LIMIT ?",
            (MAX_REPORTES,),
        ).fetchall()
    return [
        Reporte(id=str(id_), semaforoId=semaforo_id, ubicacion=ubicacion, fecha=fecha, descripcion=descripcion)
        for id_, semaforo_id, ubicacion, fecha, descripcion in rows
    ]
