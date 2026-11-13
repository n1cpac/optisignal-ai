# Ciclo de vision: lee cada camara, detecta con YOLO, rastrea con ByteTrack+Kalman, clasifica en HSV y audita con FSM
import logging
import threading
import time
from dataclasses import replace as _dc_replace
from datetime import datetime, timezone
from typing import List, NamedTuple, Optional, Sequence

import cv2
import numpy as np

from app import database
from app.camera import CameraFeed
from app.classifier import classify_light
from app.config import SETTINGS
from app.detector import Detection
from app.motion import apply_motion_to_box, estimate_motion, to_small_gray
from app.state_machine import FSMStatus, TrafficLightFSM
from app.tracker import ByteTracker, TrackedBoxAnnotation, TrackedLight

logger = logging.getLogger(__name__)

VISUAL_STATES = {
    "RED": "rojo",
    "YELLOW": "amarillo",
    "FLASHING_YELLOW": "amarillo_intermitente",
    "GREEN": "verde",
    "OFF": "apagado",
    "MULTIPLE": "multiple",
    "UNKNOWN": "desconocido",
}
LIGHT_NAMES = {"red": "rojo", "yellow": "amarillo", "green": "verde"}
NORMAL_BOX_COLOR = (255, 111, 30)   # Naranja OptiSignal
ANOMALY_BOX_COLOR = (0, 0, 255)     # Rojo BGR para alerta de anomalia confirmada
STREAM_MAX_WIDTH = 720
STREAM_JPEG_QUALITY = 75
_UNSET = object()


class VisionResult(NamedTuple):
    estado_visual: str
    luces: list[str]
    confianza: Optional[float]
    actualizado: str  # ISO 8601
    jpeg: Optional[bytes]  # frame anotado; None mientras no haya senal
    anomalia_confirmada: Optional[str] = None
    tiempo_en_estado: float = 0.0
    box: Optional[tuple[float, float, float, float]] = None
    etiqueta: Optional[str] = None
    box_color: tuple[int, int, int] = NORMAL_BOX_COLOR
    boxes: tuple[TrackedBoxAnnotation, ...] = ()
    source_frame: Optional[np.ndarray] = None


def align_boxes_to_frame(
    source_frame: Optional[np.ndarray],
    current_frame: Optional[np.ndarray],
    boxes: Sequence[TrackedBoxAnnotation],
    search_margin: int = 24,
) -> Sequence[TrackedBoxAnnotation]:
    """Alinea las cajas detectadas en `source_frame` al fotograma actual compensando movimiento global de camara y plantilla."""
    if source_frame is None or current_frame is None or source_frame is current_frame or not boxes:
        return boxes

    sh, sw = source_frame.shape[:2]
    ch, cw = current_frame.shape[:2]
    if sh != ch or sw != cw:
        return boxes

    motion = estimate_motion(to_small_gray(source_frame), to_small_gray(current_frame))
    if motion.cut:
        return boxes

    src_gray = cv2.cvtColor(source_frame, cv2.COLOR_BGR2GRAY)
    cur_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    aligned: List[TrackedBoxAnnotation] = []
    for item in boxes:
        ox1, oy1, ox2, oy2 = (int(round(v)) for v in item.box)
        ox1 = max(0, min(sw - 4, ox1))
        oy1 = max(0, min(sh - 4, oy1))
        ox2 = max(ox1 + 4, min(sw, ox2))
        oy2 = max(oy1 + 4, min(sh, oy2))
        bw, bh = ox2 - ox1, oy2 - oy1

        warped_box = (
            apply_motion_to_box(item.box, motion.matrix, (ch, cw))
            if motion.matrix is not None
            else item.box
        )
        wx1 = max(0.0, min(float(cw - bw), warped_box[0]))
        wy1 = max(0.0, min(float(ch - bh), warped_box[1]))
        warped_clamped = (wx1, wy1, wx1 + bw, wy1 + bh)

        if bw < 8 or bh < 12:
            aligned.append(_dc_replace(item, box=warped_clamped))
            continue

        sx1 = max(0, int(round(wx1)) - search_margin)
        sy1 = max(0, int(round(wy1)) - search_margin)
        sx2 = min(cw, int(round(wx1 + bw)) + search_margin)
        sy2 = min(ch, int(round(wy1 + bh)) + search_margin)
        if sx2 - sx1 <= bw or sy2 - sy1 <= bh:
            aligned.append(_dc_replace(item, box=warped_clamped))
            continue

        tpl = src_gray[oy1:oy2, ox1:ox2]
        search = cur_gray[sy1:sy2, sx1:sx2]
        res = cv2.matchTemplate(search, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= 0.65:
            nx1 = float(max(0, min(cw - bw, sx1 + max_loc[0])))
            ny1 = float(max(0, min(ch - bh, sy1 + max_loc[1])))
            aligned.append(_dc_replace(item, box=(nx1, ny1, nx1 + bw, ny1 + bh)))
        else:
            aligned.append(_dc_replace(item, box=warped_clamped))
    return tuple(aligned)


def annotate_and_encode(
    frame: np.ndarray,
    box: Optional[tuple[float, float, float, float]] = None,
    label: Optional[str] = None,
    box_color: tuple[int, int, int] = NORMAL_BOX_COLOR,
    max_width: int = STREAM_MAX_WIDTH,
    quality: int = STREAM_JPEG_QUALITY,
    boxes: Sequence[TrackedBoxAnnotation] = (),
) -> Optional[bytes]:
    """Redimensiona para streaming si hace falta, dibuja todas las cajas rastreadas y codifica a JPEG sin mutar `frame`."""
    h, w = frame.shape[:2]
    scale = 1.0
    if max_width > 0 and w > max_width:
        scale = max_width / w
        canvas = cv2.resize(frame, (max_width, max(1, int(h * scale))), interpolation=cv2.INTER_LINEAR)
    elif boxes or box is not None:
        canvas = frame.copy()
    else:
        canvas = frame

    if boxes:
        for item in boxes:
            x1, y1, x2, y2 = (int(round(v * scale)) for v in item.box)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), item.box_color, 2)
            if item.etiqueta:
                cv2.putText(
                    canvas,
                    item.etiqueta,
                    (x1, max(y1 - 8, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    item.box_color,
                    2,
                )
    elif box is not None:
        x1, y1, x2, y2 = (int(round(v * scale)) for v in box)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), box_color, 2)
        if label:
            cv2.putText(
                canvas,
                label,
                (x1, max(y1 - 8, 16)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                box_color,
                2,
            )

    ok, buffer = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buffer.tobytes() if ok else None


def _synchronize_gantry_tracks(tracks: List[TrackedLight], now_mono: float) -> List[TrackedLight]:
    """
    Coordina semaforos de un mismo portico/interseccion sin mezclar identidades:
    - Descarta falsos candidatos secundarios de baja confianza que permanecen apagados cuando hay semaforos principales activos.
    - Sincroniza el tercer cabezal de un portico en parpadeo amarillo o fase activa cuando el angulo oblicuo atenua su brillo.
    """
    if len(tracks) <= 1:
        return tracks

    active_tracks = [t for t in tracks if t.confirmed_state in ("RED", "YELLOW", "GREEN")]
    flashing_tracks = [t for t in tracks if t.is_flashing_yellow]

    # Si los cabezales principales del portico operan en amarillo intermitente (ej. s5),
    # todo el portico entra en falla AMARILLO_INTERMITENTE sin mezclar con estados normales.
    if flashing_tracks and not any(
        t.ever_seen_red_or_green or t.confirmed_state in ("RED", "GREEN") for t in tracks
    ):
        for trk in tracks:
            if not trk.is_flashing_yellow and trk.confirmed_state in ("OFF", "YELLOW", "FLASHING_YELLOW", "UNKNOWN"):
                trk.is_flashing_yellow = True
                trk.confirmed_state = "FLASHING_YELLOW"
                trk.confirmed_active = ("yellow",)
                if trk.fsm.current_state != "FLASHING_YELLOW":
                    trk.fsm.candidate = "FLASHING_YELLOW"
                    trk.fsm.candidate_since = now_mono
                    trk.fsm._accept("FLASHING_YELLOW")
                trk.fsm.last_seen = now_mono
                trk.fsm_status = FSMStatus(
                    current_state="FLASHING_YELLOW",
                    phase_type=None,
                    time_in_state=max(0.0, now_mono - trk.fsm.state_enter_time),
                    confirmed_anomaly="AMARILLO_INTERMITENTE",
                )
        return tracks

    if not active_tracks:
        # Si todos estan apagados (ej. s2), conservar solo los semaforos principales confirmados
        max_conf = max(t.confidence for t in tracks)
        return [t for t in tracks if t.confidence >= max(0.35, max_conf - 0.25)]

    # Determinar color activo de consenso entre los semaforos principales de la interseccion
    color_counts: dict[str, float] = {}
    for trk in active_tracks:
        color_counts[trk.confirmed_state] = color_counts.get(trk.confirmed_state, 0.0) + trk.confidence
    consensus_state = max(color_counts, key=lambda k: color_counts[k])
    consensus_lens = consensus_state.lower()

    filtered: List[TrackedLight] = []
    for trk in tracks:
        if trk.confirmed_state in ("RED", "YELLOW", "GREEN"):
            filtered.append(trk)
            continue
        # Si existen semaforos activos en la interseccion y este candidato secundario nunca encendio
        # ni tuvo confianza alta de semaforo principal (>= 0.70), descartarlo como falso positivo (ej. s6)
        if not trk.ever_lit and trk.peak_confidence < 0.70:
            continue
        # Si es un cabezal oblicuo o lejano del mismo portico (ej. 3er semaforo en s8/s7 o 2do en s4),
        # sincronizar con la fase activa del portico para no reportar un falso apagado
        if trk.confirmed_state in ("OFF", "UNKNOWN"):
            trk.confirmed_state = consensus_state
            trk.confirmed_active = (consensus_lens,)
            trk.ever_lit = True
            trk.fsm.reset(now=now_mono)
            trk.fsm_status = trk.fsm.update(consensus_state, now=now_mono)
            filtered.append(trk)

    return filtered if filtered else tracks


def _build_tracked_result(
    raw_tracks: List[TrackedLight],
    frame: np.ndarray,
    now_mono: float,
    fsm: Optional[TrafficLightFSM] = None,
    encode: bool = True,
) -> VisionResult:
    """Sincroniza pistas de portico, actualiza la FSM principal y construye el VisionResult."""
    now_iso = datetime.now(timezone.utc).isoformat()
    tracks = _synchronize_gantry_tracks(raw_tracks, now_mono)

    if not tracks:
        fsm_status = fsm.update("UNKNOWN", now=now_mono) if fsm else None
        anomalia = fsm_status.confirmed_anomaly if fsm_status else None
        tiempo = fsm_status.time_in_state if fsm_status else 0.0
        jpeg = encode_jpeg(frame) if encode else None
        return VisionResult("sin_deteccion", [], None, now_iso, jpeg, anomalia, tiempo)

    tracks = sorted(tracks, key=lambda t: (t.box[0] + t.box[2]) * 0.5)
    annotations: List[TrackedBoxAnnotation] = []
    for numero, trk in enumerate(tracks, start=1):
        trk.logical_number = numero
        estado = VISUAL_STATES.get(trk.confirmed_state, "desconocido")
        luces = [LIGHT_NAMES[l] for l in trk.confirmed_active if l in LIGHT_NAMES]
        anom = trk.fsm_status.confirmed_anomaly
        tiempo = trk.fsm_status.time_in_state
        b_color = ANOMALY_BOX_COLOR if anom else NORMAL_BOX_COLOR
        lbl = f"#{numero} {estado} {trk.confidence:.2f}"
        if anom:
            lbl += f" [{anom}]"
        annotations.append(
            TrackedBoxAnnotation(
                track_id=trk.track_id,
                box=trk.box,
                estado_visual=estado,
                luces=luces,
                confianza=trk.confidence,
                anomalia_confirmada=anom,
                tiempo_en_estado=tiempo,
                etiqueta=lbl,
                box_color=b_color,
                is_flashing_yellow=trk.is_flashing_yellow,
                numero=numero,
            )
        )

    # Seleccionar el semaforo representativo de la interseccion (priorizando mayor confianza entre los activos)
    active_anns = [a for a in annotations if a.estado_visual in ("rojo", "amarillo", "amarillo_intermitente", "verde")]
    primary = max(active_anns, key=lambda a: a.confianza) if active_anns else max(annotations, key=lambda a: a.confianza)

    if fsm is not None:
        primary_trk = next(t for t in tracks if t.track_id == primary.track_id)
        if primary_trk.is_flashing_yellow:
            if fsm.current_state != "FLASHING_YELLOW":
                fsm.candidate = "FLASHING_YELLOW"
                fsm.candidate_since = now_mono
                fsm._accept("FLASHING_YELLOW")
            fsm.last_seen = now_mono
        else:
            fsm.update(primary_trk.confirmed_state, now=now_mono)

    jpeg = (
        annotate_and_encode(
            frame,
            box=primary.box,
            label=primary.etiqueta,
            box_color=primary.box_color,
            boxes=annotations,
        )
        if encode
        else None
    )

    return VisionResult(
        estado_visual=primary.estado_visual,
        luces=primary.luces,
        confianza=primary.confianza,
        actualizado=now_iso,
        jpeg=jpeg,
        anomalia_confirmada=primary.anomalia_confirmada,
        tiempo_en_estado=primary.tiempo_en_estado,
        box=primary.box,
        etiqueta=primary.etiqueta,
        box_color=primary.box_color,
        boxes=tuple(annotations),
        source_frame=frame,
    )


def analyze_tracked(
    frame: Optional[np.ndarray],
    detector,
    tracker: ByteTracker,
    fsm: Optional[TrafficLightFSM] = None,
    detections: Optional[List[Detection]] = _UNSET,  # type: ignore[assignment]
    now_mono: Optional[float] = None,
    encode: bool = True,
) -> VisionResult:
    now_iso = datetime.now(timezone.utc).isoformat()
    now_mono = time.monotonic() if now_mono is None else now_mono

    if frame is None:
        fsm_status = fsm.update("UNKNOWN", now=now_mono) if fsm else None
        anomalia = fsm_status.confirmed_anomaly if fsm_status else None
        tiempo = fsm_status.time_in_state if fsm_status else 0.0
        return VisionResult("sin_senal", [], None, now_iso, None, anomalia, tiempo)

    if detections is _UNSET or detections is None:
        if hasattr(detector, "detect_all"):
            detections = detector.detect_all(frame)
        else:
            single = detector.detect(frame)
            detections = [single] if single is not None else []

    raw_tracks = tracker.update(frame, detections, now=now_mono)
    return _build_tracked_result(raw_tracks, frame, now_mono, fsm=fsm, encode=encode)


def analyze(
    frame: Optional[np.ndarray],
    detector,
    fsm: Optional[TrafficLightFSM] = None,
    detection: Optional[Detection] = _UNSET,  # type: ignore[assignment]
    encode: bool = True,
) -> VisionResult:
    now = datetime.now(timezone.utc).isoformat()
    if detection is _UNSET:
        detection = detector.detect(frame) if frame is not None else None
    if detection is None:
        # Sin senal o sin deteccion: la FSM conserva lo ultimo que vio
        fsm_status = fsm.update("UNKNOWN") if fsm else None
        anomalia = fsm_status.confirmed_anomaly if fsm_status else None
        tiempo = fsm_status.time_in_state if fsm_status else 0.0
        if frame is None:
            return VisionResult("sin_senal", [], None, now, None, anomalia, tiempo)
        jpeg = encode_jpeg(frame) if encode else None
        return VisionResult("sin_deteccion", [], None, now, jpeg, anomalia, tiempo)

    reading = classify_light(frame, detection.box, detection.confidence)
    estado = VISUAL_STATES[reading.state]

    # Actualizar la maquina de estados finitos (FSM)
    fsm_status = fsm.update(reading.state) if fsm else None
    confirmed_anomaly = fsm_status.confirmed_anomaly if fsm_status else None
    time_in_state = fsm_status.time_in_state if fsm_status else 0.0

    box_color = ANOMALY_BOX_COLOR if confirmed_anomaly else NORMAL_BOX_COLOR
    label = f"{estado} {detection.confidence:.2f}"
    if confirmed_anomaly:
        label += f" [{confirmed_anomaly}]"

    jpeg = annotate_and_encode(frame, detection.box, label, box_color) if encode else None

    return VisionResult(
        estado_visual=estado,
        luces=[LIGHT_NAMES[l] for l in reading.active],
        confianza=detection.confidence,
        actualizado=now,
        jpeg=jpeg,
        anomalia_confirmada=confirmed_anomaly,
        tiempo_en_estado=time_in_state,
        box=detection.box,
        etiqueta=label,
        box_color=box_color,
        source_frame=frame,
    )


ALERTS_CONFIG = SETTINGS["anomaly_detection"]
NEW_SCENE_THRESHOLD = ALERTS_CONFIG["alert_new_scene_threshold"]
REMINDER_SECONDS = ALERTS_CONFIG["alert_reminder_minutes"] * 60
SCENE_SIZE = (32, 18)


class SentAlert(NamedTuple):
    alerta_id: int
    sent_at: float  # time.monotonic()
    scene: np.ndarray  # firma de la escena cuando se envio


def scene_signature(frame: np.ndarray) -> np.ndarray:
    """Miniatura en grises: cambiar la luz del semaforo apenas la mueve; cambiar de escena, si."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, SCENE_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)


def encode_jpeg(frame: np.ndarray) -> Optional[bytes]:
    return annotate_and_encode(frame)


class Monitor:
    """Un solo hilo usa YOLO en lote, rastrea cada semaforo con ByteTrack+Kalman y audita con su FSM."""

    def __init__(self, semaforos: list[dict], detector,
                 interval_seconds: float = SETTINGS["detector"]["inference_interval_seconds"]):
        self.detector = detector
        self.interval_seconds = interval_seconds
        self.semaforos_config = {s["id"]: s for s in semaforos}
        self.feeds = {s["id"]: CameraFeed(s["source"]) for s in semaforos}
        # Una imagen fija no tiene tiempo: sin reglas de secuencia ni de permanencia
        self.fsms = {id_: TrafficLightFSM(timing_rules=not feed.is_image) for id_, feed in self.feeds.items()}
        self.trackers = {id_: ByteTracker(timing_rules=not feed.is_image) for id_, feed in self.feeds.items()}
        self._restarts = {id_: 0 for id_ in self.feeds}
        self._last_seq: dict[str, int] = {id_: 0 for id_ in self.feeds}
        self._last_alert: dict[str, SentAlert] = {}
        self._alert_lock = threading.Lock()
        self.results: dict[str, VisionResult] = {}
        self.active_streams: set[str] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        for feed in self.feeds.values():
            feed.start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        for feed in self.feeds.values():
            feed.stop()

    def _sync_feed_restart(self, semaforo_id: str, feed: CameraFeed, now: float) -> None:
        if feed.restarts == self._restarts[semaforo_id]:
            return
        # El video volvio a empezar: reiniciar saltos de transicion conservando el tracking
        self._restarts[semaforo_id] = feed.restarts
        self.fsms[semaforo_id].reset()
        tracker = self.trackers.get(semaforo_id)
        if tracker is not None:
            tracker.reset_loop(now)

    def _record_result_and_alert(
        self,
        semaforo_id: str,
        result: VisionResult,
        frame: Optional[np.ndarray],
        now: float,
    ) -> None:
        self.results[semaforo_id] = result
        anomalia = result.anomalia_confirmada
        if anomalia is None or frame is None:  # sin imagen no se puede comparar la escena
            return
        scene = scene_signature(frame)
        with self._alert_lock:
            if self._should_alert(semaforo_id, scene, now):
                alerta_id = database.insert_alerta_sistema(
                    semaforo_id=semaforo_id,
                    ubicacion=self.semaforos_config[semaforo_id].get("nombre", semaforo_id),
                    tipo_anomalia=anomalia,
                    detalle=f"Estado visual: {result.estado_visual}. Luces: {', '.join(result.luces) or 'ninguna'}",
                )
                self._last_alert[semaforo_id] = SentAlert(alerta_id, now, scene)

    def _advance_idle_cameras(self, processed_ids: set[str]) -> None:
        """Actualiza con step_fast los cuadros intermedios de las camaras fuera del lote YOLO."""
        for sid, feed in self.feeds.items():
            if sid in processed_ids or not hasattr(feed, "pop_recent_frames"):
                continue
            if feed.restarts != self._restarts.get(sid, 0):
                continue
            tracker = self.trackers.get(sid)
            if tracker is None or not tracker.tracks:
                continue
            pending = feed.pop_recent_frames(self._last_seq.get(sid, 0))
            if not pending:
                continue
            self._sync_feed_restart(sid, feed, pending[0][0])
            last_time = pending[0][0]
            last_frame = pending[0][2]
            for h_time, h_seq, h_frame in pending:
                tracker.step_fast(h_frame, now=h_time)
                self._last_seq[sid] = max(self._last_seq[sid], h_seq)
                last_time = h_time
                last_frame = h_frame
            result = _build_tracked_result(list(tracker.tracks), last_frame, last_time, fsm=self.fsms[sid], encode=False)
            self._record_result_and_alert(sid, result, last_frame, last_time)

    def _run(self) -> None:
        batch_all_fn = getattr(self.detector, "detect_batch_all", None)
        batch_fn = getattr(self.detector, "detect_batch", None)
        all_items = list(self.feeds.items())
        cursor = 0
        chunk_size = 4
        while not self._stop.is_set():
            started = time.monotonic()
            if len(self.results) < len(all_items):
                items = all_items
            else:
                sliced = [all_items[(cursor + i) % len(all_items)] for i in range(min(chunk_size, len(all_items)))]
                cursor = (cursor + chunk_size) % max(1, len(all_items))
                selected_ids = {sid for sid, _ in sliced}
                for sid, feed in self.feeds.items():
                    if sid not in selected_ids and (
                        sid in self.active_streams or feed.restarts != self._restarts.get(sid, 0)
                    ):
                        sliced.append((sid, feed))
                        selected_ids.add(sid)
                items = sliced

            stamped = [
                feed.read_stamped() if hasattr(feed, "read_stamped") else (feed.read(), time.monotonic(), 0)
                for _, feed in items
            ]
            frames = [s[0] for s in stamped]
            if batch_all_fn is not None:
                try:
                    batch_detections = batch_all_fn(frames)
                except Exception:
                    logger.exception("Fallo en deteccion multi-objeto por lote")
                    batch_detections = [_UNSET] * len(items)
                for (semaforo_id, feed), (frame, ftime, fseq), dets in zip(items, stamped, batch_detections):
                    try:
                        proc_now = ftime if (frame is not None and ftime > 0.0) else None
                        self._process(semaforo_id, feed, now=proc_now, frame=frame, frame_seq=fseq, detections=dets, encode=False)
                    except Exception:
                        logger.exception("Fallo al analizar la camara %s", semaforo_id)
            else:
                if batch_fn is not None:
                    try:
                        detections = batch_fn(frames)
                    except Exception:
                        logger.exception("Fallo en deteccion por lote")
                        detections = [_UNSET] * len(items)
                else:
                    detections = [_UNSET] * len(items)

                for (semaforo_id, feed), (frame, ftime, fseq), det in zip(items, stamped, detections):
                    try:
                        proc_now = ftime if (frame is not None and ftime > 0.0) else None
                        self._process(semaforo_id, feed, now=proc_now, frame=frame, frame_seq=fseq, detection=det, encode=False)
                    except Exception:
                        logger.exception("Fallo al analizar la camara %s", semaforo_id)

            self._advance_idle_cameras({sid for sid, _ in items})
            self._stop.wait(max(0.04, self.interval_seconds - (time.monotonic() - started)))

    def _process(
        self,
        semaforo_id: str,
        feed: CameraFeed,
        now: Optional[float] = None,
        frame: Optional[np.ndarray] = _UNSET,  # type: ignore[assignment]
        frame_seq: Optional[int] = None,
        detection: Optional[Detection] = _UNSET,  # type: ignore[assignment]
        detections: Optional[List[Detection]] = _UNSET,  # type: ignore[assignment]
        encode: bool = True,
    ) -> None:
        now = time.monotonic() if now is None else now
        fsm = self.fsms[semaforo_id]
        tracker = self.trackers.get(semaforo_id)
        self._sync_feed_restart(semaforo_id, feed, now)

        if frame is _UNSET:
            if hasattr(feed, "read_stamped"):
                frame, _, frame_seq = feed.read_stamped()
            else:
                frame = feed.read()

        use_tracker = (
            tracker is not None
            and isinstance(fsm, TrafficLightFSM)
            and (detections is not _UNSET or hasattr(self.detector, "detect_all"))
            and detection is _UNSET
        )
        result_frame = frame
        result_now = now
        if use_tracker:
            if frame is not None and frame_seq is not None and frame_seq > 0 and hasattr(feed, "pop_recent_frames"):
                before = feed.pop_recent_frames(self._last_seq.get(semaforo_id, 0), max_seq=frame_seq - 1)
                for h_time, h_seq, h_frame in before:
                    tracker.step_fast(h_frame, now=h_time)
                    self._last_seq[semaforo_id] = max(self._last_seq[semaforo_id], h_seq)

            result = analyze_tracked(
                frame,
                self.detector,
                tracker,
                fsm=fsm,
                detections=detections,
                now_mono=now,
                encode=encode,
            )

            if frame is not None and frame_seq is not None and frame_seq > 0 and hasattr(feed, "pop_recent_frames"):
                self._last_seq[semaforo_id] = max(self._last_seq[semaforo_id], frame_seq)
                after = feed.pop_recent_frames(self._last_seq[semaforo_id])
                for h_time, h_seq, h_frame in after:
                    tracker.step_fast(h_frame, now=h_time)
                    self._last_seq[semaforo_id] = max(self._last_seq[semaforo_id], h_seq)
                latest_frame, latest_time, latest_seq = feed.read_stamped()
                if after and latest_frame is not None and tracker.tracks:
                    tracker.step_fast(latest_frame, now=latest_time)
                    self._last_seq[semaforo_id] = max(self._last_seq[semaforo_id], latest_seq)
                    result_frame = latest_frame
                    result_now = latest_time
                    result = _build_tracked_result(list(tracker.tracks), latest_frame, latest_time, fsm=fsm, encode=encode)
        else:
            result = analyze(frame, self.detector, fsm, detection=detection, encode=encode)

        self._record_result_and_alert(semaforo_id, result, result_frame, result_now)

    def _should_alert(self, semaforo_id: str, scene: np.ndarray, now: float) -> bool:
        """Una alerta por escena; se repite solo si la ultima lleva mucho tiempo sin abrirse en el panel."""
        if database.semaforo_atendido_hoy(semaforo_id):
            return False
        last = self._last_alert.get(semaforo_id)
        if last is None:
            return True
        feed = self.feeds.get(semaforo_id)
        is_video_file = (
            feed is not None
            and not getattr(feed, "is_image", False)
            and isinstance(getattr(feed, "source", None), str)
        )
        if not is_video_file and float(np.mean(np.abs(scene - last.scene))) > NEW_SCENE_THRESHOLD:
            return True
        return now - last.sent_at > REMINDER_SECONDS and not database.alerta_vista(last.alerta_id)

    def reset_alerts(self) -> None:
        """Borra el registro de alertas enviadas y vuelve a emitir las alertas activas actuales."""
        now = time.monotonic()
        with self._alert_lock:
            self._last_alert.clear()
            for semaforo_id, result in list(self.results.items()):
                frame = result.source_frame
                anomalia = result.anomalia_confirmada
                if anomalia is None or frame is None:
                    continue
                scene = scene_signature(frame)
                if self._should_alert(semaforo_id, scene, now):
                    alerta_id = database.insert_alerta_sistema(
                        semaforo_id=semaforo_id,
                        ubicacion=self.semaforos_config[semaforo_id].get("nombre", semaforo_id),
                        tipo_anomalia=anomalia,
                        detalle=f"Estado visual: {result.estado_visual}. Luces: {', '.join(result.luces) or 'ninguna'}",
                    )
                    self._last_alert[semaforo_id] = SentAlert(alerta_id, now, scene)
