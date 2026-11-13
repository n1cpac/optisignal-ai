# Test de verificación integral del pipeline de Bogotá:
# Modelo unificado optisignal_best.pt + Cámaras CCTV s1 a s8 + ByteTrack + Kalman + Clasificación Temporal
from pathlib import Path
import cv2
import pytest

from app.config import ROOT, SETTINGS
from app.detector import Detector
from app.classifier import classify_light
from app.monitor import analyze_tracked
from app.state_machine import TrafficLightFSM
from app.tracker import ByteTracker

MODEL_PATH = ROOT / "models" / "optisignal_best.pt"
VIDEOS_DIR = ROOT / "data" / "test_videos"


@pytest.fixture(scope="module")
def shared_detector():
    return Detector(SETTINGS["detector"])


def _run_video_sample(detector: Detector, sid: str, frame_indices: list[int]):
    vid_path = VIDEOS_DIR / f"cctv_{sid}.mp4"
    cap = cv2.VideoCapture(str(vid_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    tracker = ByteTracker(timing_rules=True)
    fsm = TrafficLightFSM(timing_rules=True)
    results = []
    for fidx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ok, frame = cap.read()
        if not ok:
            continue
        res = analyze_tracked(frame, detector, tracker, fsm=fsm, now_mono=fidx / fps, encode=False)
        results.append(res)
    cap.release()
    return results, tracker, fsm


def test_unified_model_exists():
    assert MODEL_PATH.exists(), f"No se encontró el modelo {MODEL_PATH}"


def test_all_eight_bogota_videos_exist():
    for i in range(1, 9):
        vid = VIDEOS_DIR / f"cctv_s{i}.mp4"
        assert vid.exists(), f"No se encontró el video {vid}"
        assert vid.stat().st_size > 500_000, f"Video {vid} parece incompleto o vacío"


def test_detection_on_bogota_cameras(shared_detector):
    detected_cameras = 0
    for i in range(1, 9):
        vid_p = VIDEOS_DIR / f"cctv_s{i}.mp4"
        cap = cv2.VideoCapture(str(vid_p))
        det = None
        for frame_idx in (0, 15, 30):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            det = shared_detector.detect(frame)
            if det is not None:
                break
        cap.release()
        if det is not None:
            detected_cameras += 1
            assert det.confidence >= 0.25, f"Confianza baja en s{i}: {det.confidence:.2f}"
    assert detected_cameras == 8, f"Se esperaba detectar semáforos en las 8 cámaras reales, obtuvo {detected_cameras}"


def test_unlit_camera_s2_reports_off(shared_detector):
    """Caso 2 (CL 17 con KR 106): semáforo permanentemente apagado mantiene ALL_LIGHTS_OFF estable."""
    results, tracker, fsm = _run_video_sample(shared_detector, "s2", [0, 15, 30, 45, 60, 90, 120])
    assert all(r.estado_visual == "apagado" for r in results)
    assert results[-1].anomalia_confirmada == "ALL_LIGHTS_OFF"
    # Al reiniciar el bucle del video no debe perder la condición ALL_LIGHTS_OFF
    tracker.reset_loop(now=5.0)
    cap = cv2.VideoCapture(str(VIDEOS_DIR / "cctv_s2.mp4"))
    ok, frame0 = cap.read()
    cap.release()
    assert ok
    res_after_loop = analyze_tracked(frame0, shared_detector, tracker, fsm=fsm, now_mono=5.2, encode=False)
    assert res_after_loop.estado_visual == "apagado"
    assert res_after_loop.anomalia_confirmada == "ALL_LIGHTS_OFF"


def test_caso1_s7_two_red_lights_no_false_all_lights_off(shared_detector):
    """Caso 1 (AK 104 con AC 145): detecta ambos semáforos en rojo sin generar ALL_LIGHTS_OFF."""
    results, _, _ = _run_video_sample(shared_detector, "s7", [0, 30, 60, 90, 120, 150, 180])
    for r in results:
        assert len(r.boxes) >= 2
        assert r.estado_visual == "rojo"
        assert r.anomalia_confirmada is None


def test_caso3_s5_three_flashing_yellow_lights(shared_detector):
    """Caso 3 (KR 14 con CL 44 S): detecta los 3 semáforos en amarillo intermitente indefinido como falla AMARILLO_INTERMITENTE."""
    results, _, _ = _run_video_sample(shared_detector, "s5", [0, 8, 16, 24, 32, 48, 56, 64])
    for r in results[1:]:
        assert len(r.boxes) == 3
        assert r.estado_visual in ("amarillo", "amarillo_intermitente")
    for r in results[3:]:
        assert r.estado_visual == "amarillo_intermitente"
        assert r.anomalia_confirmada == "AMARILLO_INTERMITENTE"
        assert all(b.estado_visual == "amarillo_intermitente" for b in r.boxes)


def test_caso4_s1_night_flashing_yellow(shared_detector):
    """Caso 4 (AK 80 con AC 55 S): identifica amarillo intermitente nocturno y reporta falla AMARILLO_INTERMITENTE."""
    results, _, _ = _run_video_sample(shared_detector, "s1", [0, 4, 8, 12, 16, 20, 24, 28, 32])
    assert any(r.estado_visual == "amarillo_intermitente" for r in results)
    flashing_idx = next(i for i, r in enumerate(results) if r.estado_visual == "amarillo_intermitente")
    for r in results[flashing_idx:]:
        assert r.estado_visual == "amarillo_intermitente"
        assert r.anomalia_confirmada == "AMARILLO_INTERMITENTE"
    assert all(r.anomalia_confirmada != "ALL_LIGHTS_OFF" for r in results)


def test_caso5_s8_multi_lights_independent_no_false_off(shared_detector):
    """Caso 5 (AK 104 con AC 72): detecta los 3 semáforos visibles y transiciona amarillo -> rojo sin falsos apagados."""
    results, _, _ = _run_video_sample(shared_detector, "s8", [0, 30, 60, 90, 120, 150, 180])
    for r in results:
        assert len(r.boxes) >= 3
        assert r.estado_visual in ("amarillo", "rojo")
        assert r.anomalia_confirmada is None
        assert all(b.estado_visual in ("amarillo", "rojo") for b in r.boxes)


def test_caso6_s4_distant_small_lights_detected(shared_detector):
    """Caso 6 (AC 26 con KR 19): detecta ambos semáforos lejanos al fondo."""
    results, _, _ = _run_video_sample(shared_detector, "s4", [0, 25, 50, 75, 100, 125])
    assert all(len(r.boxes) >= 2 for r in results)
    assert all(r.estado_visual in ("rojo", "amarillo", "verde") for r in results)
    assert all(r.estado_visual == "verde" for r in results[2:])


def test_caso7_s6_single_green_light_no_pedestrian_false_positive(shared_detector):
    """Caso 7 (AK 7 con CL 84): detecta exclusivamente el semáforo en verde sin asociar peatones cercanos."""
    results, _, _ = _run_video_sample(shared_detector, "s6", [0, 40, 80, 120, 160, 200, 240, 280])
    for r in results:
        assert len(r.boxes) == 1
        assert r.estado_visual == "verde"
        assert r.anomalia_confirmada is None


def test_caso8_s3_two_green_lights_persistent_tracking(shared_detector):
    """Caso 8 (KR 92 con CL 169B): mantiene la detección e identidad de ambos semáforos en verde."""
    results, _, _ = _run_video_sample(shared_detector, "s3", [0, 60, 120, 180, 240, 300, 360, 420, 480])
    for r in results:
        assert len(r.boxes) == 2
        assert r.estado_visual == "verde"
        assert [b.track_id for b in r.boxes] == [1, 2]
        assert all(b.estado_visual == "verde" for b in r.boxes)


def test_s7_loop_reanchor_caps_three_boxes_and_numbers_left_to_right(shared_detector):
    """AK 104 con AC 145: conserva maximo 3 cajas numeradas #1..#3 de izquierda a derecha incluso al reiniciar el bucle."""
    results, tracker, fsm = _run_video_sample(shared_detector, "s7", [0, 45, 90, 135, 180, 208])
    for r in results:
        assert 1 <= len(r.boxes) <= 3
        numeros = [b.numero for b in r.boxes]
        assert numeros == list(range(1, len(r.boxes) + 1))
        xs = [(b.box[0] + b.box[2]) * 0.5 for b in r.boxes]
        assert xs == sorted(xs)

    tracker.reset_loop(now=16.0)
    cap = cv2.VideoCapture(str(VIDEOS_DIR / "cctv_s7.mp4"))
    ok, frame0 = cap.read()
    cap.release()
    assert ok
    res_loop = analyze_tracked(frame0, shared_detector, tracker, fsm=fsm, now_mono=16.2, encode=False)
    assert len(res_loop.boxes) <= 3
    assert [b.numero for b in res_loop.boxes] == list(range(1, len(res_loop.boxes) + 1))
    assert res_loop.estado_visual == "rojo"
    assert res_loop.anomalia_confirmada is None


def test_s8_full_cycle_never_false_flashing_yellow(shared_detector):
    """AK 104 con AC 72: en todo su ciclo de 222 frames nunca debe generar AMARILLO_INTERMITENTE."""
    frames = list(range(0, 222, 4))
    results, _, _ = _run_video_sample(shared_detector, "s8", frames)
    assert len(results) > 30
    for r in results:
        assert len(r.boxes) <= 3
        assert r.estado_visual != "amarillo_intermitente"
        assert r.anomalia_confirmada != "AMARILLO_INTERMITENTE"
        assert all(b.estado_visual != "amarillo_intermitente" for b in r.boxes)
