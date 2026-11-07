# FastAPI main application
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app import database
from app.config import SETTINGS
from app.detector import Detector
from app.models import EnvioReporte, Reporte, Semaforo
from app.monitor import Monitor, VisionResult

SEMAFOROS = {s["id"]: s for s in SETTINGS["semaforos"]}
STREAM_INTERVAL_SECONDS = SETTINGS["detector"]["inference_interval_seconds"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    monitor = Monitor(SETTINGS["semaforos"], Detector())
    monitor.start()
    app.state.monitor = monitor
    yield
    monitor.stop()


app = FastAPI(title="OptiSignal", lifespan=lifespan)


def to_semaforo(config: dict, result: VisionResult | None) -> Semaforo:
    tiene_anomalia = (result.anomalia_confirmada is not None) if (result and result.anomalia_confirmada) else config.get("falla", False)
    return Semaforo(
        id=config["id"],
        nombre=config["nombre"],
        lat=config["lat"],
        lng=config["lng"],
        estadoOperativo="anomalia" if tiene_anomalia else "normal",
        estadoElectrico=config["electrico"],
        estadoVisual=result.estado_visual if result else "sin_senal",
        lucesDetectadas=result.luces if result else [],
        confianza=result.confianza if result else None,
        imagenUrl=f"/camaras/{config['id']}/mjpeg",
        ultimaActualizacion=result.actualizado if result else datetime.now(timezone.utc).isoformat(),
    )


@app.get("/semaforos")
def get_semaforos() -> list[Semaforo]:
    results = app.state.monitor.results
    return [to_semaforo(config, results.get(id_)) for id_, config in SEMAFOROS.items()]


@app.get("/reportes")
def get_reportes() -> list[Reporte]:
    return database.list_reportes()


@app.post("/reportes/envio")
def enviar_reporte(envio: EnvioReporte) -> dict[str, bool]:
    config = SEMAFOROS.get(envio.semaforoId)
    if config is None:
        raise HTTPException(status_code=404, detail="Semaforo no encontrado")
    database.insert_reporte(envio, config["nombre"])
    return {"ok": True}


@app.get("/camaras/{semaforo_id}/mjpeg")
async def camara_mjpeg(semaforo_id: str) -> StreamingResponse:
    if semaforo_id not in SEMAFOROS:
        raise HTTPException(status_code=404, detail="Semaforo no encontrado")

    async def frames():
        while True:
            result = app.state.monitor.results.get(semaforo_id)
            if result and result.jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + result.jpeg + b"\r\n"
            await asyncio.sleep(STREAM_INTERVAL_SECONDS)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")
