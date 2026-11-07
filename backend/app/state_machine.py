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

# Parametros de ventana de confirmacion
ANOMALY_CONFIG = SETTINGS.get("anomaly_detection", {})
DEFAULT_CONFIRMATION_FRAMES = ANOMALY_CONFIG.get("confirmation_frames", 8)


@dataclass
class FSMStatus:
    current_state: str  # ROJO, AMARILLO_PREP, VERDE, AMARILLO_DESP, OFF, MULTIPLE, UNKNOWN
    phase_type: Optional[str]  # PREPARATION, CLEARANCE o None
    time_in_state: float  # Segundos acumulados en el estado actual
    candidate_anomaly: Optional[str]  # Posible anomalia detectada en el frame actual
    confirmed_anomaly: Optional[str]  # Anomalia confirmada tras superar N frames consecutivos
    anomaly_frames: int  # Contador de frames consecutivos de la anomalia candidata
    is_normal: bool  # True si el semaforo opera sin anomalia confirmada


class TrafficLightFSM:
    """
    Maquina de Estados Finitos que audita la secuencia vehicular colombiana:
    ROJO -> AMARILLO_PREP -> VERDE -> AMARILLO_DESP -> ROJO

    Incorpora:
    1. Distincion automatica de amarillo (preparacion vs despeje segun el estado previo).
    2. Deteccion de transiciones invalidas (saltos ilegales de secuencia).
    3. Deteccion de luz atascada (LIGHT_STUCK por superar tau_max).
    4. Deteccion de luces multiples (MULTIPLE_LIGHTS_ON) y apagado total (ALL_LIGHTS_OFF).
    5. Histeresis temporal: confirmacion tras N fotogramas continuos para evitar falsos positivos.
    """

    def __init__(self, confirmation_frames: int = DEFAULT_CONFIRMATION_FRAMES,
                 tau_max: Optional[dict] = None):
        self.confirmation_frames = confirmation_frames
        self.tau_max = tau_max or TAU_MAX

        self.current_state = "STARTUP"
        self.last_major_state: Optional[str] = None  # "ROJO" o "VERDE"
        self.state_enter_time = time.monotonic()
        self.last_update_time = time.monotonic()

        self.candidate_anomaly: Optional[str] = None
        self.confirmed_anomaly: Optional[str] = None
        self.anomaly_counter = 0

    def reset(self) -> None:
        """Reinicia el estado de la FSM."""
        self.current_state = "STARTUP"
        self.last_major_state = None
        self.state_enter_time = time.monotonic()
        self.last_update_time = time.monotonic()
        self.candidate_anomaly = None
        self.confirmed_anomaly = None
        self.anomaly_counter = 0

    def update(self, visual_state: str, now: Optional[float] = None) -> FSMStatus:
        """
        Procesa un nuevo estado visual (RED, YELLOW, GREEN, OFF, MULTIPLE, UNKNOWN)
        y actualiza la FSM evaluando transiciones, tiempos y anomalias.
        """
        current_time = now if now is not None else time.monotonic()
        dt = max(0.0, current_time - self.last_update_time)
        self.last_update_time = current_time

        # 1. Resolver el estado observado mapeado
        observed_state = self._resolve_observed_state(visual_state)
        frame_anomaly: Optional[str] = None

        # 2. Evaluar anomalias inmediatas por estado fisico
        if visual_state == "MULTIPLE":
            frame_anomaly = "MULTIPLE_LIGHTS_ON"
        elif visual_state == "OFF":
            frame_anomaly = "ALL_LIGHTS_OFF"
        elif visual_state == "UNKNOWN":
            # UNKNOWN es una condicion de perdida transitoria de vision, no cambia estado nominal
            time_in_state = current_time - self.state_enter_time
            return FSMStatus(
                current_state=self.current_state,
                phase_type=self._get_phase_type(),
                time_in_state=time_in_state,
                candidate_anomaly=self.candidate_anomaly,
                confirmed_anomaly=self.confirmed_anomaly,
                anomaly_frames=self.anomaly_counter,
                is_normal=self.confirmed_anomaly is None,
            )

        # 3. Transicion de estado y chequeo de secuencia legal colombiana
        if frame_anomaly is None:
            if self.current_state == "STARTUP":
                # Primer estado detectado valido
                self.current_state = observed_state
                self.state_enter_time = current_time
                if observed_state in ("ROJO", "VERDE"):
                    self.last_major_state = observed_state
            elif observed_state != self.current_state:
                # Ocurrio un cambio de color -> validar la transicion
                is_valid = self._is_valid_transition(self.current_state, observed_state)
                if is_valid:
                    self.current_state = observed_state
                    self.state_enter_time = current_time
                    if observed_state in ("ROJO", "VERDE"):
                        self.last_major_state = observed_state
                else:
                    frame_anomaly = "INVALID_TRANSITION"

        # 4. Chequeo de permanencia excesiva (LIGHT_STUCK)
        time_in_state = current_time - self.state_enter_time
        max_duration = self.tau_max.get(self.current_state)
        if frame_anomaly is None and max_duration is not None and time_in_state > max_duration:
            frame_anomaly = "LIGHT_STUCK"

        # 5. Gestion de histeresis / ventana de confirmacion de anomalia (N frames)
        if frame_anomaly is not None:
            if frame_anomaly == self.candidate_anomaly:
                self.anomaly_counter += 1
            else:
                self.candidate_anomaly = frame_anomaly
                self.anomaly_counter = 1

            if self.anomaly_counter >= self.confirmation_frames:
                self.confirmed_anomaly = frame_anomaly
        else:
            # Operacion nominal en este fotograma: enfriar contador
            self.candidate_anomaly = None
            self.anomaly_counter = max(0, self.anomaly_counter - 1)
            if self.anomaly_counter == 0:
                self.confirmed_anomaly = None

        return FSMStatus(
            current_state=self.current_state,
            phase_type=self._get_phase_type(),
            time_in_state=time_in_state,
            candidate_anomaly=self.candidate_anomaly,
            confirmed_anomaly=self.confirmed_anomaly,
            anomaly_frames=self.anomaly_counter,
            is_normal=self.confirmed_anomaly is None,
        )

    def _resolve_observed_state(self, visual_state: str) -> str:
        """Deduce si el amarillo observado es de preparacion o despeje segun el historial."""
        if visual_state == "RED":
            return "ROJO"
        if visual_state == "GREEN":
            return "VERDE"
        if visual_state == "YELLOW":
            # Si el ultimo estado principal fue ROJO, el amarillo prepara el verde
            if self.last_major_state == "ROJO":
                return "AMARILLO_PREP"
            # Si el ultimo estado principal fue VERDE, el amarillo despeja hacia el rojo
            if self.last_major_state == "VERDE":
                return "AMARILLO_DESP"
            # Por defecto en arranque: AMARILLO_DESP
            return "AMARILLO_DESP"
        return visual_state

    def _is_valid_transition(self, current: str, target: str) -> bool:
        """Secuencia estricta colombiana."""
        valid_transitions = {
            "ROJO": {"AMARILLO_PREP"},
            "AMARILLO_PREP": {"VERDE"},
            "VERDE": {"AMARILLO_DESP"},
            "AMARILLO_DESP": {"ROJO"},
        }
        return target in valid_transitions.get(current, set())

    def _get_phase_type(self) -> Optional[str]:
        if self.current_state == "AMARILLO_PREP":
            return "PREPARATION"
        if self.current_state == "AMARILLO_DESP":
            return "CLEARANCE"
        return None
