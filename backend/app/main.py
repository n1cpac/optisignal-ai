# FastAPI main application
import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app import database
from app.config import ROOT, SETTINGS
from app.detector import Detector
from app.models import EnvioReporte, PaginaReportes, Semaforo
from app.monitor import Monitor, VisionResult
from app.ubicacion import MallaVial

LIGHTS = {"rojo", "amarillo", "verde"}


def with_random_renders(semaforos: list[dict], rng: random.Random = random.Random()) -> list[dict]:
    """Una fuente que es carpeta recibe un render al azar, distinto para cada semaforo.

    El nombre del render (escenario_NN_hora_luces.png) es el estado simulado en Blender: de ahi
    salen el estado electrico y la falla. Una obstruccion no cambiaria el estado electrico.
    """
    pools: dict[Path, list[Path]] = {}
    result = []
    for semaforo in semaforos:
        source = semaforo["source"]
        folder = ROOT / source if isinstance(source, str) else None  # un numero es una camara
        if folder is None or not folder.is_dir():
            result.append(semaforo)
            continue
        if folder not in pools:
            pools[folder] = sorted(folder.glob("*.png"))
            rng.shuffle(pools[folder])
        if not pools[folder]:
            raise ValueError(f"No quedan renders en {folder} para {semaforo['id']}")
        render = pools[folder].pop()
        token = render.stem.rsplit("_", 1)[-1]
        luces = [] if token == "ninguna" else token.split("+")
        if not set(luces) <= LIGHTS:
            raise ValueError(f"Nombre de render no reconocido: {render.name}")
        electrico = "apagado" if not luces else luces[0] if len(luces) == 1 else "multiple"
        result.append({**semaforo, "source": str(render), "electrico": electrico,
                       "luces_electricas": luces, "falla": len(luces) != 1})
    return result


def with_positions(semaforos: list[dict], ruta_malla: Path = ROOT / SETTINGS["road_network"]) -> list[dict]:
    """Un semaforo sin lat/lng se ubica en el cruce que dice su nombre ('AC 72 con KR 13')."""
    faltan = [s for s in semaforos if "lat" not in s or "lng" not in s]
    if not faltan:
        return semaforos
    malla = MallaVial(ruta_malla)  # se carga solo si hace falta: son unos 25 MB
    ubicados = []
    for semaforo in semaforos:
        if semaforo in faltan:
            try:
                lat, lng = malla.cruce(semaforo["nombre"])
            except ValueError as error:
                raise ValueError(f"Semaforo {semaforo['id']}: {error}") from None
            semaforo = {**semaforo, "lat": lat, "lng": lng}
        ubicados.append(semaforo)
    return ubicados


SEMAFOROS = {s["id"]: s for s in with_positions(with_random_renders(SETTINGS["semaforos"]))}
STREAM_INTERVAL_SECONDS = SETTINGS["detector"]["inference_interval_seconds"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init()
    database.archivar_alertas_movidas({s["id"]: s["nombre"] for s in SEMAFOROS.values()})
    monitor = Monitor(list(SEMAFOROS.values()), Detector())
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
        lucesElectricas=config.get("luces_electricas",
                                   [] if config["electrico"] == "apagado" else [config["electrico"]]),
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
def get_reportes(
    vista: Literal["actuales", "historial"] = "actuales",
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=database.MAX_REPORTES),
) -> PaginaReportes:
    items, total, ultimo_id = database.list_reportes(vista, pagina, tamano)
    return PaginaReportes(items=items, total=total, pagina=pagina, tamano=tamano, ultimoId=ultimo_id)


@app.post("/reportes/{alerta_id}/abrir")
def abrir_alerta(alerta_id: int) -> dict[str, bool]:
    if not database.abrir_alerta(alerta_id):
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"ok": True}


@app.get("/reportes/{reporte_id}/escena")
def escena_reporte(reporte_id: int) -> FileResponse:
    """Escena para un reporte del historial: un render al azar, siempre el mismo para el mismo reporte."""
    escenas = sorted((ROOT / SETTINGS["history_scenes"]).glob("*.png"))
    if not escenas:
        raise HTTPException(status_code=404, detail="No hay escenas disponibles")
    return FileResponse(escenas[random.Random(reporte_id).randrange(len(escenas))], media_type="image/png")


@app.post("/reportes/envio")
def enviar_reporte(envio: EnvioReporte) -> dict[str, bool | str]:
    config = SEMAFOROS.get(envio.semaforoId)
    if config is None:
        raise HTTPException(status_code=404, detail="Semaforo no encontrado")
    reporte_id = database.insert_reporte(envio, config["nombre"])
    return {"ok": True, "id": str(reporte_id)}  # el panel abre la entrada nueva del historial


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
