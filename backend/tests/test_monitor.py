import time

import cv2
import numpy as np

from app.camera import CameraFeed
from app.detector import Detection
from app.monitor import analyze


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
    finally:
        feed.stop()


def test_stalled_source_reports_no_signal(tmp_path):
    feed = CameraFeed(str(tmp_path / "no_existe.avi"), timeout_seconds=0.1)
    feed.start()
    try:
        assert feed.read() is None
    finally:
        feed.stop()
