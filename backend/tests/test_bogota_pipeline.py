# Test de verificación integral del pipeline de Bogotá:
# Modelo unificado optisignal_best.pt + Cámaras CCTV s1 a s8 + Detección de fallas
from pathlib import Path
import cv2
import pytest
from ultralytics import YOLO

from app.config import ROOT, SETTINGS
from app.detector import Detector
from app.classifier import classify_light
from app.monitor import analyze
from app.state_machine import TrafficLightFSM

MODEL_PATH = ROOT / "models" / "optisignal_best.pt"
VIDEOS_DIR = ROOT / "data" / "test_videos"


def test_unified_model_exists():
    assert MODEL_PATH.exists(), f"No se encontró el modelo {MODEL_PATH}"


def test_all_eight_bogota_videos_exist():
    for i in range(1, 9):
        vid = VIDEOS_DIR / f"cctv_s{i}.mp4"
        assert vid.exists(), f"No se encontró el video {vid}"
        assert vid.stat().st_size > 500_000, f"Video {vid} parece incompleto o vacío"


def test_detection_confidence_on_all_cameras():
    detector = Detector(SETTINGS["detector"])
    for i in range(1, 9):
        vid_p = VIDEOS_DIR / f"cctv_s{i}.mp4"
        cap = cv2.VideoCapture(str(vid_p))
        ret, frame = cap.read()
        cap.release()
        assert ret, f"Fallo al leer frame inicial de cctv_s{i}.mp4"

        det = detector.detect(frame)
        assert det is not None, f"No se detectó semáforo en cctv_s{i}.mp4"
        assert det.confidence >= 0.80, f"Confianza baja en s{i}: {det.confidence:.2f}"


def test_failure_simulation_camera_s6_all_lights_off():
    """Valida que la cámara s6 detecta el estado apagado tras el corte de energía."""
    detector = Detector(SETTINGS["detector"])
    cap = cv2.VideoCapture(str(VIDEOS_DIR / "cctv_s6.mp4"))
    # Leer en el segundo 5 (frame 50 de 150)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 50)
    ret, frame = cap.read()
    cap.release()
    assert ret

    det = detector.detect(frame)
    assert det is not None
    reading = classify_light(frame, det.box, det.confidence)
    assert reading.state == "OFF", f"s6 debería reportar OFF tras el apagón, obtuvo: {reading.state}"


def test_failure_simulation_camera_s7_multiple_lights_on():
    """Valida que la cámara s7 detecta conflicto eléctrico (doble luz encendida simultáneamente)."""
    detector = Detector(SETTINGS["detector"])
    cap = cv2.VideoCapture(str(VIDEOS_DIR / "cctv_s7.mp4"))
    # Leer en el segundo 5 (frame 50 de 150)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 50)
    ret, frame = cap.read()
    cap.release()
    assert ret

    det = detector.detect(frame)
    assert det is not None
    reading = classify_light(frame, det.box, det.confidence)
    assert reading.state == "MULTIPLE", f"s7 debería reportar MULTIPLE en falla, obtuvo: {reading.state}"
    assert set(reading.active) == {"red", "green"}
