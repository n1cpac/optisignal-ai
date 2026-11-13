import time

import cv2
import numpy as np
import pytest

from app import database
from app.camera import CameraFeed
from app.detector import Detection
from app.monitor import Monitor, analyze
from app.state_machine import FSMStatus


class StubDetector:
    def __init__(self, detection):
        self.detection = detection

    def detect(self, frame):
        return self.detection


def red_light_frame():
    hsv = np.zeros((120, 60, 3), dtype=np.uint8)
    hsv[10:40, 10:40] = (4, 60, 255)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def test_no_signal_is_not_a_missing_detection():
    result = analyze(None, StubDetector(None))
    assert (result.estado_visual, result.jpeg) == ("sin_senal", None)


def test_missing_detection_still_shows_the_frame():
    result = analyze(red_light_frame(), StubDetector(None))
    assert result.estado_visual == "sin_deteccion"
    assert result.jpeg.startswith(b"\xff\xd8")


def test_detection_is_classified_without_touching_the_shared_frame():
    frame = red_light_frame()
    original = frame.copy()
    result = analyze(frame, StubDetector(Detection((10, 10, 40, 100), 0.9)))
    assert (result.estado_visual, result.luces, result.confianza) == ("rojo", ["rojo"], 0.9)
    assert np.array_equal(frame, original)


def wait_for_frame(feed, seconds=3.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if (frame := feed.read()) is not None:
            return frame
        time.sleep(0.02)
    return None


def test_video_source_keeps_delivering_frames_after_it_ends(tmp_path):
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for _ in range(3):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    feed = CameraFeed(str(path), timeout_seconds=0.5)
    feed.start()
    try:
        assert wait_for_frame(feed) is not None
        time.sleep(1.0)  # el clip dura 0,1 s: sin bucle, read() ya daria None
        assert feed.read() is not None
        assert feed.restarts >= 1
    finally:
        feed.stop()


class FakeFeed:
    is_image = False

    def __init__(self):
        self.restarts = 0
        self.frame = red_light_frame()

    def read(self):
        return self.frame


class ScriptedFSM:
    """Devuelve las anomalias en el orden dado y cuenta los reinicios."""

    def __init__(self, anomalies):
        self.anomalies = iter(anomalies)
        self.resets = 0

    def update(self, visual_state, now=None):
        return FSMStatus("ROJO", None, 0.0, next(self.anomalies))

    def reset(self):
        self.resets += 1


def monitor_with(fsm):
    monitor = Monitor([{"id": "s1", "nombre": "AC 13 con CL 13", "source": "img.png"}],
                      StubDetector(Detection((10, 10, 40, 100), 0.9)))
    monitor.feeds["s1"] = FakeFeed()
    monitor.fsms["s1"] = fsm
    return monitor


class ConstantFSM:
    """Siempre reporta la misma anomalia (o ninguna)."""

    def __init__(self, anomaly):
        self.anomaly = anomaly

    def update(self, visual_state, now=None):
        return FSMStatus("ROJO", None, 0.0, self.anomaly)

    def reset(self):
        pass


@pytest.fixture
def alerts(monkeypatch):
    """Registra las alertas enviadas; `seen` son las que el operador ya abrio o atendio."""
    sent, seen = [], set()
    monkeypatch.setattr(database, "insert_alerta_sistema", lambda **kw: sent.append(kw["tipo_anomalia"]) or len(sent))
    monkeypatch.setattr(database, "alerta_vista", lambda alerta_id: alerta_id in seen)
    monkeypatch.setattr(database, "semaforo_atendido_hoy", lambda semaforo_id: False)
    return sent, seen


def other_scene():
    return np.full((120, 60, 3), 200, dtype=np.uint8)


def test_one_alert_per_scene_even_if_the_anomaly_continues_or_changes(alerts):
    sent, _ = alerts
    fsm = ConstantFSM("ALL_LIGHTS_OFF")
    monitor = monitor_with(fsm)
    for t in range(5):
        monitor._process("s1", monitor.feeds["s1"], now=t)
    fsm.anomaly = "LIGHT_STUCK"
    monitor._process("s1", monitor.feeds["s1"], now=6)
    assert sent == ["ALL_LIGHTS_OFF"]

    monitor.feeds["s1"].frame = other_scene()  # nueva semilla en Blender
    monitor._process("s1", monitor.feeds["s1"], now=7)
    monitor._process("s1", monitor.feeds["s1"], now=8)
    assert sent == ["ALL_LIGHTS_OFF", "LIGHT_STUCK"]


def test_a_light_change_in_the_same_scene_is_not_a_new_scene(alerts):
    sent, _ = alerts
    monitor = monitor_with(ConstantFSM("MULTIPLE_LIGHTS_ON"))

    def street_with_light(row, hsv_color):
        # Proporciones de una camara: el lente (14 px) es diminuto frente a la escena de 1280x720
        hsv = np.full((720, 1280, 3), (100, 40, 120), dtype=np.uint8)
        hsv[row:row + 14, 600:614] = hsv_color
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    monitor.feeds["s1"].frame = street_with_light(300, (4, 60, 255))  # rojo
    monitor._process("s1", monitor.feeds["s1"], now=0)
    monitor.feeds["s1"].frame = street_with_light(340, (63, 25, 255))  # ahora verde
    monitor._process("s1", monitor.feeds["s1"], now=1)
    assert len(sent) == 1


def test_an_unopened_alert_is_repeated_after_the_reminder_time(alerts):
    sent, seen = alerts
    monitor = monitor_with(ConstantFSM("ALL_LIGHTS_OFF"))
    monitor._process("s1", monitor.feeds["s1"], now=0)
    monitor._process("s1", monitor.feeds["s1"], now=29 * 60)
    assert len(sent) == 1
    monitor._process("s1", monitor.feeds["s1"], now=31 * 60)
    assert len(sent) == 2

    seen.add(2)  # el operador abrio el recordatorio: no se repite mas en esta escena
    monitor._process("s1", monitor.feeds["s1"], now=70 * 60)
    assert len(sent) == 2


def test_no_alert_without_anomaly_or_without_image(alerts):
    sent, _ = alerts
    monitor = monitor_with(ConstantFSM(None))
    monitor._process("s1", monitor.feeds["s1"], now=0)
    monitor.fsms["s1"] = ConstantFSM("ALL_LIGHTS_OFF")
    monitor.feeds["s1"].frame = None
    monitor._process("s1", monitor.feeds["s1"], now=1)
    assert sent == []


def test_a_video_restart_resets_its_state_machine():
    fsm = ScriptedFSM([None] * 3)
    monitor = monitor_with(fsm)
    monitor._process("s1", monitor.feeds["s1"])
    monitor.feeds["s1"].restarts = 1
    monitor._process("s1", monitor.feeds["s1"])
    monitor._process("s1", monitor.feeds["s1"])
    assert fsm.resets == 1


def test_static_images_get_a_state_machine_without_timing_rules():
    monitor = Monitor([{"id": "s1", "nombre": "x", "source": "img.png"},
                       {"id": "s2", "nombre": "y", "source": "clip.mp4"}], StubDetector(None))
    assert (monitor.fsms["s1"].timing_rules, monitor.fsms["s2"].timing_rules) == (False, True)


def test_stalled_source_reports_no_signal(tmp_path):
    feed = CameraFeed(str(tmp_path / "no_existe.avi"), timeout_seconds=0.1)
    feed.start()
    try:
        assert feed.read() is None
    finally:
        feed.stop()


def test_an_electrical_fault_alerts_even_if_yolo_sees_everything_fine(alerts):
    sent, _ = alerts
    monitor = monitor_with(ConstantFSM(None))
    monitor.semaforos_config["s1"]["falla"] = True
    monitor._process("s1", monitor.feeds["s1"], now=0)
    monitor._process("s1", monitor.feeds["s1"], now=1)  # misma escena: no repite
    assert sent == ["ELECTRICAL_FAULT"]


def test_a_vision_anomaly_keeps_its_own_type_when_the_electrical_system_also_fails(alerts):
    sent, _ = alerts
    monitor = monitor_with(ConstantFSM("ALL_LIGHTS_OFF"))
    monitor.semaforos_config["s1"]["falla"] = True
    monitor._process("s1", monitor.feeds["s1"], now=0)
    assert sent == ["ALL_LIGHTS_OFF"]
