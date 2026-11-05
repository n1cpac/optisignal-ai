# Data models and schemas
# Los nombres en camelCase son el contrato de core/models del panel Angular.
from typing import Literal, Optional

from pydantic import BaseModel, Field

EstadoLuz = Literal["rojo", "amarillo", "verde", "apagado"]
EstadoVisual = Literal[
    "rojo", "amarillo", "verde", "apagado", "multiple", "sin_deteccion", "desconocido", "sin_senal"
]


class Semaforo(BaseModel):
    id: str
    nombre: str
    lat: float
    lng: float
    estadoOperativo: Literal["normal", "anomalia"]
    estadoElectrico: EstadoLuz
    estadoVisual: EstadoVisual
    lucesDetectadas: list[Literal["rojo", "amarillo", "verde"]]
    confianza: Optional[float]
    fuenteImagen: Literal["url"] = "url"
    imagenUrl: str
    ultimaActualizacion: str


class Reporte(BaseModel):
    id: str
    semaforoId: str
    ubicacion: str
    fecha: str
    descripcion: str


class EnvioReporte(BaseModel):
    semaforoId: str
    coincide: bool
    comentario: str = Field(max_length=2000)
    destinatarios: list[Literal["transito", "tecnicos"]] = Field(min_length=1)
