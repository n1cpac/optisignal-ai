# Test de integracion real de extremo a extremo (E2E)
# Valida: Video real (test1.mp4) -> Detector YOLO (models/lisa_best.pt) -> Clasificador HSV -> FSM -> SQLite

import time
import cv2
import pytest

from app import database
from app.config import ROOT
from app.detector import Detector
from app.classifier import classify_light
from app.state_machine import TrafficLightFSM
from app.monitor import analyze

VIDEO_PATH = ROOT / "data" / "test_videos" / "test1.mp4"
requires_video = pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Video de prueba no disponible")


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_integration.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init()
    return db_file


def read_frame(index):
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    assert ok, f"No se pudo leer el frame {index} de test1.mp4"
    return frame


@requires_video
def test_real_yolo_detection_and_hsv_classification():
    """Valida que el modelo real lisa_best.pt localiza el semaforo y clasifica su color en test1.mp4."""
    frame = read_frame(60)

    # Ejecutar detector real con los pesos entrenados actuales
    detector = Detector()
    detection = detector.detect(frame)

    assert detection is not None, "El detector con lisa_best.pt debe localizar el semaforo"
    assert detection.confidence >= 0.25, f"Confianza esperada >= 0.25, obtenida: {detection.confidence}"

    # Clasificar el color de la caja encontrada por YOLO
    reading = classify_light(frame, detection.box, detection.confidence)
    assert reading.state == "GREEN", f"Se esperaba luz GREEN, clasificador retorno {reading.state}"
    assert "green" in reading.active


@requires_video
def test_real_pipeline_end_to_end_with_fsm_and_db(test_db):
    """Valida el ciclo completo Video -> YOLO -> HSV -> FSM -> Persistencia de Alerta con test1.mp4."""
    green_frame = read_frame(60)  # luz verde
    yellow_frame = read_frame(300)  # luz amarilla de despeje

    detector = Detector()
    # Confirmacion inmediata y tau_max bajo (0.5 s) para validar semaforo trabado (LIGHT_STUCK)
    fsm = TrafficLightFSM(confirmation_seconds=0, tau_max={"VERDE": 1.0, "AMARILLO_DESP": 0.5})

    # 1. Procesar frames normales (el semaforo opera en VERDE)
    for _ in range(3):
        result = analyze(green_frame, detector, fsm)
        assert result.estado_visual == "verde"
        assert result.anomalia_confirmada is None

    # 2. Procesar transicion valida a amarillo
    result = analyze(yellow_frame, detector, fsm)
    assert result.estado_visual == "amarillo"
    assert result.anomalia_confirmada is None

    # 3. Simular semaforo trabado manteniendo el amarillo mas alla de tau_max (0.5 s)
    t_base = time.monotonic()
    for step in range(1, 5):
        st = fsm.update("YELLOW", now=t_base + step * 0.25)

    assert st.confirmed_anomaly == "LIGHT_STUCK"

    # 4. Persistir la alerta confirmada en base de datos SQLite
    database.insert_alerta_sistema(
        semaforo_id="s1",
        ubicacion="AC 13 con CL 13",
        tipo_anomalia=st.confirmed_anomaly,
        detalle="Luz amarilla de despeje excedio el tiempo maximo de permanencia"
    )

    reportes, _, _ = database.list_reportes("actuales")
    assert len(reportes) >= 1
    assert "LIGHT_STUCK" in reportes[0].descripcion
    assert reportes[0].ubicacion == "AC 13 con CL 13"


@requires_video
def test_looping_video_never_reports_a_sequence_error():
    """Dos vueltas de test1.mp4 a 4 Hz, reiniciando la FSM en cada vuelta como hace el monitor."""
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    detector = Detector()
    fsm = TrafficLightFSM()
    stride = round(fps / 4)
    anomalies = set()
    states = [
        classify_light(frame, detection.box, detection.confidence).state if detection else "UNKNOWN"
        for frame in frames[::stride]
        for detection in [detector.detect(frame)]
    ]
    duration = len(frames) / fps
    for lap in range(2):
        fsm.reset(now=lap * duration)
        for i, state in enumerate(states):
            # Tiempo del video, no del reloj: la prueba no depende de cuanto tarda YOLO
            anomalies.add(fsm.update(state, now=lap * duration + i * stride / fps).confirmed_anomaly)

    assert not anomalies & {"INVALID_TRANSITION", "LIGHT_STUCK"}, anomalies
