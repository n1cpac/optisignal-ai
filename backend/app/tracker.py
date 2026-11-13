# Multi-object tracker (ByteTrack + 2D Kalman Filter + Temporal State Window per Traffic Light ID)
from collections import deque
from dataclasses import dataclass
import time
from typing import List, Optional, Sequence

import cv2
import numpy as np

from app.classifier import LightReading, classify_light
from app.config import SETTINGS
from app.detector import Detection, box_iou
from app.motion import SmallGray, apply_motion_to_box, estimate_motion, to_small_gray
from app.state_machine import FSMStatus, TrafficLightFSM

TRACKER_SETTINGS = SETTINGS.get("detector", {}).get("tracker", {})


def _xyxy_to_cxcywh(box: Sequence[float]) -> np.ndarray:
    x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
    return np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5, max(4.0, x2 - x1), max(8.0, y2 - y1)], dtype=np.float64)


def _cxcywh_to_xyxy(state: np.ndarray, frame_shape: Optional[tuple[int, int]] = None) -> tuple[float, float, float, float]:
    cx, cy, w, h = float(state[0]), float(state[1]), max(4.0, float(state[2])), max(8.0, float(state[3]))
    x1 = cx - w * 0.5
    y1 = cy - h * 0.5
    x2 = cx + w * 0.5
    y2 = cy + h * 0.5
    if frame_shape is not None:
        fh, fw = frame_shape
        x1 = max(0.0, min(float(fw - 2), x1))
        y1 = max(0.0, min(float(fh - 2), y1))
        x2 = max(x1 + 2.0, min(float(fw), x2))
        y2 = max(y1 + 4.0, min(float(fh), y2))
    return (x1, y1, x2, y2)


class KalmanBoxFilter:
    """
    Filtro de Kalman 2D de velocidad constante sobre [cx, cy, w, h, vx, vy]
    con control de cambios bruscos de dimension (evita que peatones cercanos
    deformen la caja del semaforo) y amortiguacion de deriva sin introducir retraso.
    """

    def __init__(
        self,
        init_box: Sequence[float],
        process_noise: float = TRACKER_SETTINGS.get("kalman_process_noise", 0.03),
        measurement_noise: float = TRACKER_SETTINGS.get("kalman_measurement_noise", 0.15),
        max_size_change_ratio: float = TRACKER_SETTINGS.get("max_size_change_ratio", 0.18),
    ):
        self.max_size_change_ratio = max_size_change_ratio
        cx, cy, w, h = _xyxy_to_cxcywh(init_box)
        self.x = np.array([cx, cy, w, h, 0.0, 0.0], dtype=np.float64)
        self.P = np.diag([10.0, 10.0, 15.0, 15.0, 100.0, 100.0]).astype(np.float64)
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

    def predict(self, dt: float = 1.0, shift: tuple[float, float] = (0.0, 0.0)) -> tuple[float, float, float, float]:
        dt = max(0.02, min(2.0, float(dt)))
        F = np.eye(6, dtype=np.float64)
        F[0, 4] = dt
        F[1, 5] = dt

        # Aplicar compensacion de paneo global de camara si existe; no extrapolar con inercia propia
        if abs(shift[0]) > 0.5 or abs(shift[1]) > 0.5:
            self.x[0] += shift[0]
            self.x[1] += shift[1]
            self.x[4] = 0.0
            self.x[5] = 0.0
        else:
            self.x[4] = 0.0
            self.x[5] = 0.0
            self.x = F @ self.x

        scale = max(16.0, self.x[3])
        q_pos = (self.process_noise * scale) ** 2
        q_size = (self.process_noise * 0.35 * scale) ** 2
        q_vel = (self.process_noise * 1.5 * scale) ** 2
        Q = np.diag([q_pos, q_pos, q_size, q_size, q_vel, q_vel])
        self.P = F @ self.P @ F.T + Q
        return _cxcywh_to_xyxy(self.x[:4])

    def update(self, measured_box: Sequence[float], confidence: float = 1.0) -> tuple[float, float, float, float]:
        z = _xyxy_to_cxcywh(measured_box)
        cur_w, cur_h = self.x[2], self.x[3]

        # Control de cambios bruscos en dimensiones: limita expansiones/contracciones subitas
        # (por ejemplo cuando pasa una persona junto al semaforo en s6)
        max_dw = cur_w * self.max_size_change_ratio
        max_dh = cur_h * self.max_size_change_ratio
        clamped_w = float(np.clip(z[2], cur_w - max_dw, cur_w + max_dw))
        clamped_h = float(np.clip(z[3], cur_h - max_dh, cur_h + max_dh))

        # Si el ancho medido crecio de forma anomala (>30%) respecto al historico del semaforo
        # mientras el semaforo esta practicamente estatico, anclar el centro para evitar desvios hacia intrusos
        disp = float(np.hypot(z[0] - self.x[0], z[1] - self.x[1]))
        if z[2] > cur_w * 1.30 and disp < cur_w * 0.35:
            z[0] = 0.70 * self.x[0] + 0.30 * z[0]
        z[2] = clamped_w
        z[3] = clamped_h

        # Si hay desplazamiento real por paneo/movimiento de camara (> 3.0 px), seguir la medicion sin retraso espacial
        if disp > 3.0:
            self.x[0] = z[0]
            self.x[1] = z[1]
            self.x[2] = clamped_w
            self.x[3] = clamped_h
            self.x[4] = 0.0
            self.x[5] = 0.0
            return _cxcywh_to_xyxy(self.x[:4])

        H = np.zeros((4, 6), dtype=np.float64)
        H[0, 0] = H[1, 1] = H[2, 2] = H[3, 3] = 1.0

        conf_weight = max(0.25, min(1.0, float(confidence)))
        r_pos = ((self.measurement_noise / conf_weight) * max(12.0, cur_h * 0.12)) ** 2
        r_size = ((self.measurement_noise / conf_weight) * max(16.0, cur_h * 0.22)) ** 2
        R = np.diag([r_pos, r_pos, r_size, r_size])

        y = z - (H @ self.x)
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + (K @ y)
        self.P = (np.eye(6, dtype=np.float64) - K @ H) @ self.P

        # Si el desplazamiento real fue minimo, amortiguar velocidad residual para evitar deriva
        if abs(y[0]) < cur_w * 0.08:
            self.x[4] *= 0.25
        if abs(y[1]) < cur_h * 0.08:
            self.x[5] *= 0.25

        return _cxcywh_to_xyxy(self.x[:4])


@dataclass
class TrackedBoxAnnotation:
    track_id: int
    box: tuple[float, float, float, float]
    estado_visual: str
    luces: list[str]
    confianza: float
    anomalia_confirmada: Optional[str]
    tiempo_en_estado: float
    etiqueta: str
    box_color: tuple[int, int, int]
    is_flashing_yellow: bool = False
    numero: int = 1


class TrackedLight:
    """Representa un semaforo individual con ID persistente, filtro de Kalman, historial temporal y FSM."""

    def __init__(
        self,
        track_id: int,
        detection: Detection,
        now: float,
        timing_rules: bool = True,
        temporal_window_seconds: float = TRACKER_SETTINGS.get("temporal_window_seconds", 5.5),
    ):
        self.track_id = track_id
        self.logical_number: int = track_id
        self.kalman = KalmanBoxFilter(detection.box)
        self.box: tuple[float, float, float, float] = detection.box
        self.confidence: float = detection.confidence
        self.peak_confidence: float = detection.confidence
        self.ever_lit: bool = False
        self.ever_seen_red_or_green: bool = False
        self._needs_loop_reanchor: bool = False
        self.hits: int = 1
        self.age: int = 1
        self.missed_frames: int = 0
        self.created_at: float = now
        self.last_seen_time: float = now
        self.last_matched_time: float = now
        self.temporal_window_seconds = temporal_window_seconds

        self.position_history: deque[tuple[float, float, float, float]] = deque([detection.box], maxlen=30)
        self.raw_history: deque[tuple[float, str, tuple[str, ...]]] = deque(maxlen=90)
        self.confirmed_state: str = "UNKNOWN"
        self.confirmed_active: tuple[str, ...] = ()
        self.is_flashing_yellow: bool = False
        self._off_since: Optional[float] = None
        self._off_streak: int = 0
        self._multiple_streak: int = 0
        self.template_gray: Optional[np.ndarray] = None
        self.fsm = TrafficLightFSM(timing_rules=timing_rules)
        self.fsm_status: FSMStatus = self.fsm.update("UNKNOWN", now=now)

    def update_template(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = (int(round(v)) for v in self.box)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 >= 10 and y2 - y1 >= 16:
            patch = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
            self.template_gray = cv2.resize(patch, (24, 48), interpolation=cv2.INTER_AREA)

    def match_template_in_frame(self, frame: np.ndarray, search_margin: int = 28) -> Optional[tuple[tuple[float, float, float, float], float]]:
        """Verifica si la estructura fisica del semaforo sigue en su posicion cuando YOLO baja de confianza."""
        if self.template_gray is None:
            return None
        fh, fw = frame.shape[:2]
        x1, y1, x2, y2 = (int(round(v)) for v in self.box)
        bw, bh = x2 - x1, y2 - y1
        if bw < 10 or bh < 16:
            return None
        sx1 = max(0, x1 - search_margin)
        sy1 = max(0, y1 - search_margin)
        sx2 = min(fw, x2 + search_margin)
        sy2 = min(fh, y2 + search_margin)
        if sx2 - sx1 < bw or sy2 - sy1 < bh:
            return None
        search_patch = cv2.cvtColor(frame[sy1:sy2, sx1:sx2], cv2.COLOR_BGR2GRAY)
        tpl = cv2.resize(self.template_gray, (bw, bh), interpolation=cv2.INTER_LINEAR)
        res = cv2.matchTemplate(search_patch, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < 0.70:
            return None
        nx1 = float(sx1 + max_loc[0])
        ny1 = float(sy1 + max_loc[1])
        return ((nx1, ny1, nx1 + bw, ny1 + bh), float(max_val))

    def observe_visual(self, reading: LightReading, now: float, detected_this_frame: bool = True) -> FSMStatus:
        """
        Evalua el estado de funcionamiento del semaforo usando una ventana temporal por ID:
        - Reconoce el parpadeo amarillo (YELLOW <-> OFF) como estado operativo amarillo.
        - Aplica histeresis para evitar alternancias espurias ante caidas de 1-3 frames.
        - Separa la perdida momentanea de deteccion de un apagado real.
        """
        raw_state = reading.state
        raw_active = reading.active
        if (
            raw_state == "OFF"
            and self.confirmed_state == "YELLOW"
            and not self.is_flashing_yellow
            and reading.ratios.get("yellow", 0.0) >= 0.06
            and reading.ratios.get("red", 0.0) < 0.05
            and reading.ratios.get("green", 0.0) < 0.05
        ):
            raw_state = "YELLOW"
            raw_active = ("yellow",)
        if raw_state in ("RED", "YELLOW", "GREEN"):
            self.ever_lit = True

        # Si el objeto fue mantenido por prediccion (sin deteccion directa en este frame) y lee OFF/UNKNOWN,
        # no contaminar la ventana con un falso apagado si venia con un color activo confirmado
        if not detected_this_frame and raw_state in ("OFF", "UNKNOWN") and self.confirmed_state in ("RED", "YELLOW", "FLASHING_YELLOW", "GREEN"):
            if self.confirmed_state == "FLASHING_YELLOW":
                self.fsm_status = FSMStatus(
                    current_state="FLASHING_YELLOW",
                    phase_type=None,
                    time_in_state=max(0.0, now - self.created_at),
                    confirmed_anomaly="AMARILLO_INTERMITENTE",
                )
            else:
                self.fsm_status = self.fsm.update(self.confirmed_state, now=now)
            return self.fsm_status

        if raw_state != "UNKNOWN":
            self.raw_history.append((now, raw_state, raw_active))
        while self.raw_history and (now - self.raw_history[0][0]) > self.temporal_window_seconds:
            self.raw_history.popleft()

        # Analizar la ventana temporal de este semaforo
        states_in_window = [st for _, st, _ in self.raw_history]
        n_total = len(states_in_window)
        n_yellow = sum(1 for st in states_in_window if st == "YELLOW")
        n_off = sum(1 for st in states_in_window if st == "OFF")
        n_red = sum(1 for st in states_in_window if st == "RED")
        n_green = sum(1 for st in states_in_window if st == "GREEN")
        last_yellow_ts = max((t for t, st, _ in self.raw_history if st == "YELLOW"), default=None)

        # Contar alternancias reales YELLOW <-> OFF en la ventana temporal (>= 2 cambios = ciclo completo)
        yo_sequence = [st for st in states_in_window if st in ("YELLOW", "OFF")]
        yo_transitions = sum(1 for a, b in zip(yo_sequence, yo_sequence[1:]) if a != b)

        # Si aparece rojo o verde consistente, sale de modo amarillo intermitente y registra ciclo normal
        if raw_state in ("RED", "GREEN") and (n_red >= 2 or n_green >= 2):
            self.is_flashing_yellow = False
            self.ever_seen_red_or_green = True

        # 1. Deteccion de patron de amarillo intermitente (Casos 3 y 4: s5 y s1)
        # Requiere alternancia real YELLOW <-> OFF (>= 2 transiciones, ej. OFF->YELLOW->OFF o YELLOW->OFF->YELLOW)
        # sin rojo ni verde en la ventana ni historial previo de fase rojo/verde, para no confundirlo con s8.
        recent_yellow = last_yellow_ts is not None and (now - last_yellow_ts) <= 4.5
        if not self.ever_seen_red_or_green and (
            (self.is_flashing_yellow and n_red <= 1 and n_green == 0)
            or (
                recent_yellow
                and yo_transitions >= 2
                and n_yellow >= 1
                and n_off >= 1
                and n_red <= 1
                and n_green == 0
            )
        ):
            self.is_flashing_yellow = True
            self.confirmed_state = "FLASHING_YELLOW"
            self.confirmed_active = ("yellow",)
            self._off_since = None
            self._off_streak = 0
            # Confirmar inmediatamente la condicion de falla AMARILLO_INTERMITENTE en la FSM
            if self.fsm.current_state != "FLASHING_YELLOW":
                self.fsm.candidate = "FLASHING_YELLOW"
                self.fsm.candidate_since = now
                self.fsm._accept("FLASHING_YELLOW")
            self.fsm.last_seen = now
            self.fsm_status = FSMStatus(
                current_state="FLASHING_YELLOW",
                phase_type=None,
                time_in_state=max(0.0, now - self.fsm.state_enter_time),
                confirmed_anomaly="AMARILLO_INTERMITENTE",
            )
            return self.fsm_status

        # 2. Clasificacion con histeresis para estados activos y apagados (Casos 1, 2, 5, 6, 7, 8)
        if raw_state in ("RED", "YELLOW", "GREEN"):
            self._off_since = None
            self._off_streak = 0
            self._multiple_streak = 0
            # Si cambia de un color activo confirmado a otro distinto, exigir confirmacion breve (2 lecturas)
            # salvo cuando venia en UNKNOWN/OFF o cuando coincide con el color confirmado
            if self.confirmed_state in ("UNKNOWN", "OFF") or raw_state == self.confirmed_state:
                self.confirmed_state = raw_state
                self.confirmed_active = raw_active
            else:
                recent_same = sum(1 for st in states_in_window[-3:] if st == raw_state)
                if recent_same >= 2:
                    self.confirmed_state = raw_state
                    self.confirmed_active = raw_active
        elif raw_state == "MULTIPLE":
            self._multiple_streak += 1
            if self._multiple_streak >= 3 or self.confirmed_state == "MULTIPLE":
                self.confirmed_state = "MULTIPLE"
                self.confirmed_active = raw_active
            elif raw_active and self.confirmed_state in ("UNKNOWN", "OFF"):
                dom = max(raw_active, key=lambda l: reading.ratios.get(l, 0.0))
                self.confirmed_state = dom.upper()
                self.confirmed_active = (dom,)
                self.ever_lit = True
        elif raw_state == "OFF":
            self._multiple_streak = 0
            self._off_streak += 1
            if self._off_since is None:
                self._off_since = now

            if self.confirmed_state in ("RED", "YELLOW", "GREEN"):
                # Conservar el estado activo si el semaforo ya demostro estar encendido y no parpadea en amarillo
                if self.ever_lit and not self.is_flashing_yellow:
                    pass
                else:
                    # Histeresis: conservar el color activo salvo que la ausencia de luz persista
                    off_duration = now - self._off_since
                    hold_seconds = 1.60 if self.confirmed_state == "YELLOW" else 0.90
                    if off_duration >= hold_seconds and self._off_streak >= 4 and not self.is_flashing_yellow:
                        self.confirmed_state = "OFF"
                        self.confirmed_active = ()
            else:
                self.confirmed_state = "OFF"
                self.confirmed_active = ()

        if self.confirmed_state in ("RED", "YELLOW", "GREEN") and self.fsm.current_state in ("OFF", "MULTIPLE"):
            self.fsm.candidate = self.confirmed_state
            self.fsm.candidate_since = now
            self.fsm._accept(self.confirmed_state)
        self.fsm.transition_anomaly = None
        self.fsm_status = self.fsm.update(self.confirmed_state, now=now)
        if self.confirmed_state in ("RED", "YELLOW", "GREEN") and self.fsm_status.confirmed_anomaly in (
            "ALL_LIGHTS_OFF",
            "MULTIPLE_LIGHTS_ON",
            "INVALID_TRANSITION",
            "LIGHT_STUCK",
        ):
            self.fsm_status = FSMStatus(
                current_state=self.fsm_status.current_state,
                phase_type=self.fsm_status.phase_type,
                time_in_state=self.fsm_status.time_in_state,
                confirmed_anomaly=None,
            )
        elif (
            self.confirmed_state == "OFF"
            and self.fsm_status.confirmed_anomaly == "ALL_LIGHTS_OFF"
            and (
                self.ever_lit
                or self.peak_confidence < 0.75
                or (self._off_since is not None and (now - self._off_since) < 1.50)
            )
        ):
            self.fsm_status = FSMStatus(
                current_state=self.fsm_status.current_state,
                phase_type=self.fsm_status.phase_type,
                time_in_state=self.fsm_status.time_in_state,
                confirmed_anomaly=None,
            )
        return self.fsm_status

    def on_video_loop(self, now: float) -> None:
        """Al reiniciar el bucle de un video de prueba, preserva el estado confirmado y reinicia temporizadores."""
        self.last_seen_time = now
        self._needs_loop_reanchor = True
        self.fsm.last_seen = now
        self.fsm.transition_anomaly = None
        self.fsm.candidate = None
        self.fsm.last_major_state = None
        if self.confirmed_state != "OFF":
            self.fsm.state_enter_time = now


class ByteTracker:
    """
    Sistema de seguimiento multi-objeto basado en ByteTrack (asociacion en dos etapas:
    detecciones de alta confianza + recuperacion con baja confianza) acoplado con
    KalmanBoxFilter y persistencia asistida por plantilla para semaforos lejanos.
    """

    def __init__(
        self,
        timing_rules: bool = True,
        high_threshold: float = TRACKER_SETTINGS.get("high_threshold", 0.25),
        low_threshold: float = TRACKER_SETTINGS.get("low_threshold", 0.12),
        match_iou_threshold: float = TRACKER_SETTINGS.get("match_iou_threshold", 0.20),
        max_center_distance_ratio: float = TRACKER_SETTINGS.get("max_center_distance_ratio", 1.35),
        max_age_seconds: float = TRACKER_SETTINGS.get("max_age_seconds", 5.0),
        max_tracks: int = TRACKER_SETTINGS.get("max_tracks", 3),
    ):
        self.timing_rules = timing_rules
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.match_iou_threshold = match_iou_threshold
        self.max_center_distance_ratio = max_center_distance_ratio
        self.max_age_seconds = max_age_seconds
        self.max_tracks = max_tracks
        self.tracks: List[TrackedLight] = []
        self._next_id: int = 1
        self._last_time: Optional[float] = None
        self._prev_small: Optional[SmallGray] = None

    def reset_loop(self, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        self._prev_small = None
        for track in self.tracks:
            track.on_video_loop(now)

    def _affinity(self, track_box: tuple[float, float, float, float], det_box: tuple[float, float, float, float]) -> float:
        iou = box_iou(track_box, det_box)
        tc = _xyxy_to_cxcywh(track_box)
        dc = _xyxy_to_cxcywh(det_box)
        dist = float(np.hypot(tc[0] - dc[0], tc[1] - dc[1]))
        ref_diag = float(np.hypot(max(tc[2], dc[2]), max(tc[3], dc[3])))
        max_dist = self.max_center_distance_ratio * max(24.0, ref_diag)

        # Penalizar diferencias extremas de tamano para no asociar un semaforo con otro lejano
        size_ratio = min(tc[3], dc[3]) / max(tc[3], dc[3])
        if size_ratio < 0.42:
            return 0.0
        if iou >= self.match_iou_threshold:
            return 0.65 * iou + 0.35 * max(0.0, 1.0 - dist / max_dist)
        if dist <= max_dist:
            return 0.45 * (1.0 - dist / max_dist) * size_ratio
        return 0.0

    def _associate(
        self,
        track_indices: List[int],
        detections: List[Detection],
        min_score: float = 0.18,
    ) -> tuple[List[tuple[int, int]], List[int], List[int]]:
        if not track_indices or not detections:
            return [], list(track_indices), list(range(len(detections)))

        score_matrix = np.zeros((len(track_indices), len(detections)), dtype=np.float64)
        for ti, trk_idx in enumerate(track_indices):
            tbox = self.tracks[trk_idx].box
            for di, det in enumerate(detections):
                score_matrix[ti, di] = self._affinity(tbox, det.box)

        matched: List[tuple[int, int]] = []
        used_t: set[int] = set()
        used_d: set[int] = set()

        # Asignacion greedy por afinidad descendente
        flat_indices = np.argsort(-score_matrix, axis=None)
        for flat_idx in flat_indices:
            ti = int(flat_idx // len(detections))
            di = int(flat_idx % len(detections))
            if ti in used_t or di in used_d:
                continue
            if score_matrix[ti, di] < min_score:
                break
            used_t.add(ti)
            used_d.add(di)
            matched.append((track_indices[ti], di))

        unmatched_t = [track_indices[ti] for ti in range(len(track_indices)) if ti not in used_t]
        unmatched_d = [di for di in range(len(detections)) if di not in used_d]
        return matched, unmatched_t, unmatched_d

    def update(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        now: Optional[float] = None,
    ) -> List[TrackedLight]:
        now = time.monotonic() if now is None else now
        dt = 0.12 if self._last_time is None else max(0.02, min(1.0, now - self._last_time))
        self._last_time = now
        fh, fw = frame.shape[:2]

        high_dets = [d for d in detections if d.confidence >= self.high_threshold]
        low_dets = [d for d in detections if self.low_threshold <= d.confidence < self.high_threshold]

        # 0. Compensacion global de movimiento de camara y reanclaje ante corte/reinicio de bucle
        cur_small = to_small_gray(frame)
        if self._prev_small is not None and self.tracks:
            motion = estimate_motion(self._prev_small, cur_small)
            if motion.cut:
                for trk in self.tracks:
                    trk._needs_loop_reanchor = True
            elif motion.matrix is not None:
                for trk in self.tracks:
                    warped = apply_motion_to_box(trk.box, motion.matrix, (fh, fw))
                    trk.box = warped
                    trk.kalman.x[:4] = _xyxy_to_cxcywh(warped)
                    trk.kalman.x[4:] = 0.0
        self._prev_small = cur_small

        if self.tracks and any(t._needs_loop_reanchor for t in self.tracks):
            for trk in self.tracks:
                trk._needs_loop_reanchor = False
            if high_dets and len(high_dets) >= len(self.tracks):
                tracks_lr = sorted(self.tracks, key=lambda t: (t.box[0] + t.box[2]) * 0.5)
                dets_lr = sorted(high_dets, key=lambda d: (d.box[0] + d.box[2]) * 0.5)
                disps = sorted(
                    (
                        (((trk.box[0] + trk.box[2]) * 0.5) - ((det.box[0] + det.box[2]) * 0.5)) ** 2
                        + (((trk.box[1] + trk.box[3]) * 0.5) - ((det.box[1] + det.box[3]) * 0.5)) ** 2
                    ) ** 0.5
                    for trk, det in zip(tracks_lr, dets_lr)
                )
                med_disp = disps[len(disps) // 2] if disps else 0.0
                if med_disp > 40.0:
                    reanchored: List[TrackedLight] = []
                    for trk, det in zip(tracks_lr, dets_lr):
                        trk.kalman = KalmanBoxFilter(det.box)
                        trk.box = det.box
                        trk.confidence = 0.65 * det.confidence + 0.35 * trk.confidence
                        trk.peak_confidence = max(trk.peak_confidence, det.confidence)
                        trk.hits += 1
                        trk.missed_frames = 0
                        trk.last_seen_time = now
                        trk.last_matched_time = now
                        trk.position_history.append(trk.box)
                        trk.update_template(frame)
                        reanchored.append(trk)
                    self.tracks = reanchored

        # 1. Prediccion inicial de Kalman para cada track activo
        prev_boxes = {trk.track_id: trk.box for trk in self.tracks}
        for trk in self.tracks:
            trk.age += 1
            trk.box = _cxcywh_to_xyxy(_xyxy_to_cxcywh(trk.kalman.predict(dt)), (fh, fw))

        # 2. Primera etapa ByteTrack: asociar tracks con detecciones de alta confianza
        all_trk_indices = list(range(len(self.tracks)))
        matched_1, unmatched_trks_1, unmatched_high = self._associate(all_trk_indices, high_dets, min_score=0.18)

        # Calcular desplazamiento global de camara (paneo/tilt) a partir de los tracks emparejados
        shifts_x: List[float] = []
        shifts_y: List[float] = []
        for trk_idx, det_idx in matched_1:
            trk = self.tracks[trk_idx]
            det = high_dets[det_idx]
            prev_c = _xyxy_to_cxcywh(prev_boxes[trk.track_id])
            new_c = _xyxy_to_cxcywh(det.box)
            shifts_x.append(float(new_c[0] - prev_c[0]))
            shifts_y.append(float(new_c[1] - prev_c[1]))

        cam_shift = (
            float(np.median(shifts_x)) if shifts_x else 0.0,
            float(np.median(shifts_y)) if shifts_y else 0.0,
        )

        for trk_idx, det_idx in matched_1:
            trk = self.tracks[trk_idx]
            det = high_dets[det_idx]
            trk.box = _cxcywh_to_xyxy(_xyxy_to_cxcywh(trk.kalman.update(det.box, det.confidence)), (fh, fw))
            trk.confidence = 0.65 * det.confidence + 0.35 * trk.confidence
            trk.peak_confidence = max(trk.peak_confidence, det.confidence)
            trk.hits += 1
            trk.missed_frames = 0
            trk.last_seen_time = now
            trk.last_matched_time = now
            trk.position_history.append(trk.box)
            trk.update_template(frame)

        # Aplicar compensacion de paneo de camara a los tracks aun no emparejados antes de la 2da etapa
        if abs(cam_shift[0]) > 1.5 or abs(cam_shift[1]) > 1.5:
            for trk_idx in unmatched_trks_1:
                trk = self.tracks[trk_idx]
                pbox = prev_boxes[trk.track_id]
                shifted = (pbox[0] + cam_shift[0], pbox[1] + cam_shift[1], pbox[2] + cam_shift[0], pbox[3] + cam_shift[1])
                trk.kalman.x[0] = (shifted[0] + shifted[2]) * 0.5
                trk.kalman.x[1] = (shifted[1] + shifted[3]) * 0.5
                trk.box = _cxcywh_to_xyxy(trk.kalman.x[:4], (fh, fw))

        # 3. Segunda etapa ByteTrack: asociar tracks restantes con detecciones de baja confianza
        matched_2, unmatched_trks_2, _ = self._associate(unmatched_trks_1, low_dets, min_score=0.16)
        for trk_idx, det_idx in matched_2:
            trk = self.tracks[trk_idx]
            det = low_dets[det_idx]
            trk.box = _cxcywh_to_xyxy(_xyxy_to_cxcywh(trk.kalman.update(det.box, det.confidence)), (fh, fw))
            trk.confidence = max(0.26, 0.50 * det.confidence + 0.50 * trk.confidence)
            trk.hits += 1
            trk.missed_frames = 0
            trk.last_seen_time = now
            trk.last_matched_time = now
            trk.position_history.append(trk.box)
            trk.update_template(frame)

        # 3b. Si la camara hizo un paneo brusco (ej. s5), asociar tracks no emparejados con detecciones altas desplazadas
        if unmatched_trks_2 and unmatched_high:
            rem_high_dets = [high_dets[di] for di in unmatched_high]
            old_ratio = self.max_center_distance_ratio
            self.max_center_distance_ratio = max(old_ratio, 2.8)
            matched_pan, unmatched_trks_2, rem_unmatched_idx = self._associate(
                unmatched_trks_2, rem_high_dets, min_score=0.08
            )
            self.max_center_distance_ratio = old_ratio
            for trk_idx, rel_di in matched_pan:
                trk = self.tracks[trk_idx]
                det = rem_high_dets[rel_di]
                trk.kalman = KalmanBoxFilter(det.box)
                trk.box = det.box
                trk.confidence = 0.65 * det.confidence + 0.35 * trk.confidence
                trk.peak_confidence = max(trk.peak_confidence, det.confidence)
                trk.hits += 1
                trk.missed_frames = 0
                trk.last_seen_time = now
                trk.last_matched_time = now
                trk.position_history.append(trk.box)
                trk.update_template(frame)
            unmatched_high = [unmatched_high[i] for i in rem_unmatched_idx]

        # 4. Recuperacion asistida por plantilla/color para semaforos que sufren caida momentanea de YOLO
        matched_track_ids = {self.tracks[i].track_id for i in range(len(self.tracks)) if i not in unmatched_trks_2}
        if not unmatched_high:
            for trk_idx in unmatched_trks_2:
                trk = self.tracks[trk_idx]
                trk.missed_frames += 1
                tpl_match = trk.match_template_in_frame(frame)
                if tpl_match is not None:
                    matched_box, corr = tpl_match
                    probe_reading = classify_light(frame, matched_box, max(trk.confidence, 0.30))
                    if corr >= 0.78 or probe_reading.state in ("RED", "YELLOW", "GREEN"):
                        trk.box = _cxcywh_to_xyxy(_xyxy_to_cxcywh(trk.kalman.update(matched_box, 0.45)), (fh, fw))
                        trk.confidence = max(0.28, trk.confidence * 0.97)
                        if corr >= 0.78 or trk.peak_confidence >= 0.60:
                            trk.hits += 1
                            trk.missed_frames = 0
                        trk.last_seen_time = now
                        trk.position_history.append(trk.box)
                        matched_track_ids.add(trk.track_id)
                        continue
                if trk.peak_confidence >= 0.60:
                    box_reading = classify_light(frame, trk.box, max(trk.confidence, 0.30))
                    if box_reading.state in ("RED", "YELLOW", "GREEN"):
                        trk.confidence = max(0.28, trk.confidence * 0.97)
                        trk.hits += 1
                        trk.missed_frames = 0
                        trk.last_seen_time = now
                        matched_track_ids.add(trk.track_id)
        else:
            for trk_idx in unmatched_trks_2:
                self.tracks[trk_idx].missed_frames += 1

        # 5. Crear nuevos tracks para detecciones de alta confianza no asociadas y sin traslape con tracks activos
        for det_idx in unmatched_high:
            det = high_dets[det_idx]
            dc = _xyxy_to_cxcywh(det.box)
            overlaps_existing = False
            for trk in self.tracks:
                if box_iou(det.box, trk.box) >= 0.22:
                    overlaps_existing = True
                    break
                tc = _xyxy_to_cxcywh(trk.box)
                if abs(dc[0] - tc[0]) < 1.25 * max(dc[2], tc[2]) and abs(dc[1] - tc[1]) < 0.85 * max(dc[3], tc[3]):
                    overlaps_existing = True
                    break
            if not overlaps_existing:
                new_trk = TrackedLight(self._next_id, det, now=now, timing_rules=self.timing_rules)
                new_trk.update_template(frame)
                self._next_id += 1
                self.tracks.append(new_trk)
                matched_track_ids.add(new_trk.track_id)

        # 6. Depurar tracks expirados, deduplicar solapamientos y limitar al maximo de cabezales
        surviving_tracks: List[TrackedLight] = []
        for trk in self.tracks:
            age_unseen = now - trk.last_seen_time
            max_coast = self.max_age_seconds if (trk.hits >= 2 or trk.peak_confidence >= 0.60) else 0.65
            if age_unseen <= max_coast:
                surviving_tracks.append(trk)

        # Deduplicar tracks que convergieron al mismo cabezal tras un paneo
        deduped_tracks: List[TrackedLight] = []
        for trk in sorted(surviving_tracks, key=lambda t: (t.hits, t.peak_confidence, t.confidence), reverse=True):
            tc = _xyxy_to_cxcywh(trk.box)
            duplicate = False
            for kept in deduped_tracks:
                kc = _xyxy_to_cxcywh(kept.box)
                if (
                    abs(tc[0] - kc[0]) < 0.70 * max(tc[2], kc[2])
                    and abs(tc[1] - kc[1]) < 0.75 * max(tc[3], kc[3])
                ) or box_iou(trk.box, kept.box) >= 0.40:
                    duplicate = True
                    break
            if not duplicate:
                deduped_tracks.append(trk)

        if len(deduped_tracks) > self.max_tracks:
            deduped_tracks = sorted(
                deduped_tracks,
                key=lambda t: (t.hits >= 2, t.peak_confidence, t.confidence),
                reverse=True,
            )[: self.max_tracks]

        self.tracks = deduped_tracks

        # 7. Evaluar clasificacion cromatica y ventana temporal de estados por cada track activo
        for trk in self.tracks:
            was_detected = trk.track_id in matched_track_ids
            eff_conf = max(trk.confidence, SETTINGS["detector"].get("confidence_threshold", 0.25))
            reading = classify_light(frame, trk.box, eff_conf)
            trk.observe_visual(reading, now=now, detected_this_frame=was_detected)

        # Ordenar de izquierda a derecha y asignar numeracion logica (#1, #2, #3...)
        self.tracks.sort(key=lambda t: (t.box[0] + t.box[2]) * 0.5)
        for idx, trk in enumerate(self.tracks, start=1):
            trk.logical_number = idx
        return list(self.tracks)

    def step_fast(self, frame: np.ndarray, now: Optional[float] = None) -> List[TrackedLight]:
        """Compensa movimiento global de camara, refina por plantilla local y evalua el estado cromatico."""
        if not self.tracks or any(t._needs_loop_reanchor for t in self.tracks):
            return list(self.tracks)
        now = time.monotonic() if now is None else now
        fh, fw = frame.shape[:2]
        self._last_time = now

        cur_small = to_small_gray(frame)
        if self._prev_small is not None:
            motion = estimate_motion(self._prev_small, cur_small)
            if motion.cut:
                for trk in self.tracks:
                    trk._needs_loop_reanchor = True
                self._prev_small = cur_small
                return list(self.tracks)
            if motion.matrix is not None:
                for trk in self.tracks:
                    warped = apply_motion_to_box(trk.box, motion.matrix, (fh, fw))
                    trk.box = warped
                    trk.kalman.x[:4] = _xyxy_to_cxcywh(warped)
                    trk.kalman.x[4:] = 0.0
        self._prev_small = cur_small

        for trk in self.tracks:
            if trk.hits < 2 and trk.peak_confidence < 0.60:
                continue
            eff_conf = max(trk.confidence, SETTINGS["detector"].get("confidence_threshold", 0.25))
            tpl_match = trk.match_template_in_frame(frame, search_margin=24)
            if tpl_match is not None:
                matched_box, corr = tpl_match
                probe_reading = classify_light(frame, matched_box, eff_conf)
                if corr >= 0.68 or probe_reading.state in ("RED", "YELLOW", "GREEN"):
                    trk.box = _cxcywh_to_xyxy(_xyxy_to_cxcywh(trk.kalman.update(matched_box, 0.65)), (fh, fw))
                    trk.last_seen_time = now
                    trk.hits += 1
                    trk.missed_frames = 0
                    trk.position_history.append(trk.box)
                    if corr >= 0.80:
                        trk.update_template(frame)
                    trk.observe_visual(probe_reading, now=now, detected_this_frame=True)
                    continue

            reading = classify_light(frame, trk.box, eff_conf)
            if reading.state in ("RED", "YELLOW", "GREEN"):
                trk.last_seen_time = now
                trk.observe_visual(reading, now=now, detected_this_frame=True)
            elif reading.state == "OFF" and trk.confirmed_state in ("YELLOW", "FLASHING_YELLOW", "OFF", "UNKNOWN"):
                trk.last_seen_time = now
                trk.observe_visual(reading, now=now, detected_this_frame=True)

        self.tracks.sort(key=lambda t: (t.box[0] + t.box[2]) * 0.5)
        for idx, trk in enumerate(self.tracks, start=1):
            trk.logical_number = idx
        return list(self.tracks)
