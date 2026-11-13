# Finite State Machine (FSM) for Colombian Traffic Light Sequence & Anomaly Detection
from dataclasses import dataclass
from typing import Optional
import time

from app.config import SETTINGS

# Tiempos maximos nominales (tau_max) en segundos
TIMING = SETTINGS.get("traffic_light_timing", {})
TAU_MAX = {
    "ROJO": TIMING.get("red_max", 120),
    "AMARILLO_PREP": TIMING.get("yellow_prep_max", 5),
    "VERDE": TIMING.get("green_max", 90),
    "AMARILLO_DESP": TIMING.get("yellow_desp_max", 5),
}

ANOMALY_CONFIG = SETTINGS.get("anomaly_detection", {})
DEFAULT_CONFIRMATION_SECONDS = ANOMALY_CONFIG.get("state_confirmation_seconds", 1.0)
DEFAULT_RESYNC_SECONDS = ANOMALY_CONFIG.get("resync_after_seconds", 2.0)

# Secuencia colombiana: cada color solo puede pasar al siguiente
NEXT_STATE = {
    "ROJO": "AMARILLO_PREP",
    "AMARILLO_PREP": "VERDE",
    "VERDE": "AMARILLO_DESP",
    "AMARILLO_DESP": "ROJO",
}
# Fallas que duran mientras el semaforo esta en ese estado
CONDITION_ANOMALIES = {
    "OFF": "ALL_LIGHTS_OFF",
    "MULTIPLE": "MULTIPLE_LIGHTS_ON",
    "FLASHING_YELLOW": "AMARILLO_INTERMITENTE",
}


@dataclass
class FSMStatus:
    current_state: str  # STARTUP, ROJO, AMARILLO_PREP, VERDE, AMARILLO_DESP, OFF o MULTIPLE
    phase_type: Optional[str]  # PREPARATION, CLEARANCE o None
    time_in_state: float  # Segundos en el estado actual, hasta la ultima vez que se vio el semaforo
    confirmed_anomaly: Optional[str]


class TrafficLightFSM:
    """
    Maquina de Estados Finitos que audita la secuencia vehicular colombiana:
    ROJO -> AMARILLO_PREP -> VERDE -> AMARILLO_DESP -> ROJO

    Trabaja en dos etapas:
    1. Confirmacion: un estado visual nuevo solo se acepta si se mantiene `confirmation_seconds`,
       asi un parpadeo o un error de un fotograma no cuenta como cambio.
    2. Reglas, una vez por cambio aceptado:
       - INVALID_TRANSITION es un evento: se marca al aceptar un salto ilegal y dura hasta el
         siguiente cambio. El estado nuevo se adopta igual, para no quedar anclado al anterior.
       - ALL_LIGHTS_OFF, MULTIPLE_LIGHTS_ON y LIGHT_STUCK son condiciones: duran mientras ocurren.

    Si el semaforo se pierde de vista mas de `resync_seconds`, el siguiente estado se acepta sin
    validar el salto: el color pudo cambiar varias veces sin que la camara lo viera.
    Con `timing_rules=False` (imagenes fijas, que no tienen tiempo) solo se evaluan las condiciones
    de apagado y luces multiples.
    """

    def __init__(self, confirmation_seconds: float = DEFAULT_CONFIRMATION_SECONDS,
                 resync_seconds: float = DEFAULT_RESYNC_SECONDS,
                 tau_max: Optional[dict] = None, timing_rules: bool = True):
        self.confirmation_seconds = confirmation_seconds
        self.resync_seconds = resync_seconds
        self.tau_max = tau_max or TAU_MAX
        self.timing_rules = timing_rules
        self.reset()

    def reset(self, now: Optional[float] = None) -> None:
        """Reinicia la FSM, por ejemplo cuando un video vuelve a empezar."""
        self.current_state = "STARTUP"
        self.last_major_state: Optional[str] = None  # "ROJO" o "VERDE"
        self.state_enter_time = time.monotonic() if now is None else now
        self.accepted_visual: Optional[str] = None  # estado visual (RED, YELLOW, ...) aceptado
        self.candidate: Optional[str] = None
        self.candidate_since = 0.0
        self.last_seen: Optional[float] = None
        self.transition_anomaly: Optional[str] = None

    def update(self, visual_state: str, now: Optional[float] = None) -> FSMStatus:
        """Procesa un estado visual (RED, YELLOW, GREEN, OFF, MULTIPLE o UNKNOWN)."""
        now = time.monotonic() if now is None else now
        # UNKNOWN es perdida de vision: no es un estado del semaforo y no cambia nada
        if visual_state != "UNKNOWN":
            if self.last_seen is not None and now - self.last_seen > self.resync_seconds:
                self.current_state = "STARTUP"
                self.accepted_visual = None
                self.candidate = None
            self.last_seen = now
            self._observe(visual_state, now)
        return self._status()

    def _observe(self, visual_state: str, now: float) -> None:
        if visual_state == self.accepted_visual:
            self.candidate = None
            return
        if visual_state != self.candidate:
            self.candidate, self.candidate_since = visual_state, now
        if now - self.candidate_since >= self.confirmation_seconds:
            self._accept(visual_state)

    def _accept(self, visual_state: str) -> None:
        new_state = self._resolve_observed_state(visual_state)
        previous = self.current_state
        if self.timing_rules and previous in NEXT_STATE and new_state in NEXT_STATE:
            self.transition_anomaly = None if NEXT_STATE[previous] == new_state else "INVALID_TRANSITION"
        else:
            # Sin un color previo confiable (arranque, falla o semaforo perdido de vista) no hay salto que validar
            self.transition_anomaly = None

        self.current_state = new_state
        self.accepted_visual = visual_state
        self.state_enter_time = self.candidate_since  # el cambio ocurrio cuando se vio por primera vez
        self.candidate = None
        if new_state in ("ROJO", "VERDE"):
            self.last_major_state = new_state

    def _status(self) -> FSMStatus:
        if self.candidate is not None:
            # Ya se ve otro color: el estado actual termino ahi, aunque el cambio aun se este confirmando
            seen_until = self.candidate_since
        else:
            seen_until = self.last_seen if self.last_seen is not None else self.state_enter_time
        time_in_state = max(0.0, seen_until - self.state_enter_time)

        anomaly = CONDITION_ANOMALIES.get(self.current_state)
        max_duration = self.tau_max.get(self.current_state)
        if anomaly is None and self.timing_rules and max_duration is not None and time_in_state > max_duration:
            anomaly = "LIGHT_STUCK"

        return FSMStatus(
            current_state=self.current_state,
            phase_type=self._get_phase_type(),
            time_in_state=time_in_state,
            confirmed_anomaly=anomaly or self.transition_anomaly,
        )

    def _resolve_observed_state(self, visual_state: str) -> str:
        """Deduce si el amarillo observado es de preparacion o despeje segun el historial."""
        if visual_state == "RED":
            return "ROJO"
        if visual_state == "GREEN":
            return "VERDE"
        if visual_state == "YELLOW":
            # Despues de ROJO el amarillo prepara el verde; despues de VERDE (o al arrancar) despeja hacia el rojo
            return "AMARILLO_PREP" if self.last_major_state == "ROJO" else "AMARILLO_DESP"
        return visual_state

    def _get_phase_type(self) -> Optional[str]:
        if self.current_state == "AMARILLO_PREP":
            return "PREPARATION"
        if self.current_state == "AMARILLO_DESP":
            return "CLEARANCE"
        return None
