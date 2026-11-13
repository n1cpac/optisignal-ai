# Data models and schemas
# Los nombres en camelCase son el contrato de core/models del panel Angular.
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

EstadoLuz = Literal["rojo", "amarillo", "verde", "apagado"]
EstadoVisual = Literal[
    "rojo", "amarillo", "amarillo_intermitente", "verde", "apagado", "multiple", "sin_deteccion", "desconocido", "sin_senal"
]
TipoFalla = Literal["funcionamiento", "dano"]


class Cabezal(BaseModel):
    """Un semaforo individual (cabezal) dentro de la interseccion, numerado de izquierda a derecha."""
    numero: int
    estadoVisual: EstadoVisual
    confianza: float
    anomalia: Optional[str] = None


class Semaforo(BaseModel):
    id: str
    nombre: str
    lat: float
    lng: float
    estadoOperativo: Literal["normal", "anomalia"]
    estadoElectrico: Literal["rojo", "amarillo", "verde", "apagado", "multiple"]
    lucesElectricas: list[Literal["rojo", "amarillo", "verde"]]
    estadoVisual: EstadoVisual
    lucesDetectadas: list[Literal["rojo", "amarillo", "verde"]]
    confianza: Optional[float]
    fuenteImagen: Literal["url"] = "url"
    imagenUrl: str
    ultimaActualizacion: str
    cabezales: list[Cabezal] = []


class Opciones(BaseModel):
    """Lo que el operador marco al confirmar un reporte desde el panel."""
    reporteId: str
    fecha: str
    coincide: bool
    falla: Optional[bool]  # None en reportes anteriores a esta opcion
    destinatarios: list[Literal["transito", "tecnicos"]]
    comentario: Optional[str]  # None en reportes anteriores a esta opcion
    tipoFalla: Optional[TipoFalla] = None  # funcionamiento (opera mal) o dano (dano fisico)
    semaforosAfectados: list[int] = []  # numeros de los cabezales con la falla


class Reporte(BaseModel):
    id: str
    semaforoId: str
    ubicacion: str
    fecha: str
    descripcion: str
    automatica: bool  # alerta del sistema de vision; si no, reporte del operador
    # Reporte del operador: sus propias opciones. Alerta: las del reporte que la atendio, o None si no se ha atendido
    opciones: Optional[Opciones]
    alertasVerificadas: int = 0  # reporte del operador: cuantas alertas verifico
    ultimaAlertaVerificada: Optional[str] = None  # descripcion de la mas reciente de ellas


class PaginaReportes(BaseModel):
    items: list[Reporte]
    total: int  # de toda la vista, no solo de esta pagina
    pagina: int
    tamano: int
    ultimoId: Optional[int]  # id mas reciente de toda la vista: si crece, llego algo nuevo


class EnvioReporte(BaseModel):
    semaforoId: str
    coincide: bool
    falla: bool  # el operador confirma que hay un fallo en el semaforo
    comentario: str = Field(max_length=2000)
    destinatarios: list[Literal["transito", "tecnicos"]] = []  # puede ir vacio, incluso con fallo
    tipoFalla: Optional[TipoFalla] = None  # solo con fallo
    semaforosAfectados: list[int] = []  # solo con fallo: numeros de cabezal (1, 2, 3...)

    @model_validator(mode="after")
    def destinatarios_solo_con_falla(self) -> "EnvioReporte":
        if self.destinatarios and not self.falla:
            raise ValueError("Solo se envia a transito o tecnicos cuando hay fallo en el semaforo")
        if (self.tipoFalla or self.semaforosAfectados) and not self.falla:
            raise ValueError("El tipo de falla y los semaforos afectados solo aplican cuando hay fallo")
        if any(n < 1 for n in self.semaforosAfectados):
            raise ValueError("Los semaforos afectados se numeran desde 1")
        self.semaforosAfectados = sorted(set(self.semaforosAfectados))
        return self
