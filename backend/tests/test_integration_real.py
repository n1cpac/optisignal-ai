# Test de integracion real de extremo a extremo (E2E)
# Valida: Video real (test1.mp4) -> Detector YOLO (models/lisa_best.pt) -> Clasificador HSV -> FSM -> SQLite

import time
import cv2
import pytest
from pathlib import Path

from app import database
from app.detector import Detector
from app.classifier import classify_light
from app.state_machine import TrafficLightFSM
from app.monitor import analyze


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_integration.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init()
    return db_file


def test_real_yolo_detection_and_hsv_classification():
    """Valida que el modelo real lisa_best.pt localiza el semaforo y clasifica su color en test1.mp4."""
    video_path = Path("data/test_videos/test1.mp4")
    if not video_path.exists():
        pytest.skip("Video de prueba no disponible")

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
    ok, frame = cap.read()
    cap.release()
    assert ok, "No se pudo leer el frame 60 de test1.mp4"

    # Ejecutar detector real con los pesos entrenados actuales
    detector = Detector()
    detection = detector.detect(frame)

    assert detection is not None, "El detector con lisa_best.pt debe localizar el semaforo"
    assert detection.confidence >= 0.25, f"Confianza esperada >= 0.25, obtenida: {detection.confidence}"

    # Clasificar el color de la caja encontrada por YOLO
    reading = classify_light(frame, detection.box, detection.confidence)
    assert reading.state == "GREEN", f"Se esperaba luz GREEN, clasificador retorno {reading.state}"
    assert "green" in reading.active


def test_real_pipeline_end_to_end_with_fsm_and_db(test_db):
    """Valida el ciclo completo Video -> YOLO -> HSV -> FSM -> Persistencia de Alerta con test1.mp4."""
    video_path = Path("data/test_videos/test1.mp4")
    if not video_path.exists():
        pytest.skip("Video de prueba no disponible")

    cap = cv2.VideoCapture(str(video_path))

    # 1. Leer frame normal (luz verde en frame 60)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
    ok_green, green_frame = cap.read()
    assert ok_green

    # 2. Leer frame de transicion a despeje (frame 300: luz amarilla)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 300)
    ok_yellow, yellow_frame = cap.read()
    cap.release()
    assert ok_yellow

    detector = Detector()
    # Configuramos tau_max bajo (0.5s) para validar deteccion de semaforo trabado (LIGHT_STUCK)
    fsm = TrafficLightFSM(confirmation_frames=3, tau_max={"VERDE": 1.0, "AMARILLO_DESP": 0.5})

    # 3. Procesar frames normales (el semaforo opera en VERDE)
    for _ in range(3):
        result = analyze(green_frame, detector, fsm)
        assert result.estado_visual == "verde"
        assert result.anomalia_confirmada is None

    # 4. Procesar transicion valida a amarillo
    result = analyze(yellow_frame, detector, fsm)
    assert result.estado_visual == "amarillo"

    # 5. Simular semaforo trabado (LIGHT_STUCK) manteniendo el estado amarillo mas alla de tau_max (0.5 s)
    t_base = time.monotonic()
    for step in range(1, 5):
        st = fsm.update("YELLOW", now=t_base + 1.0 + step * 0.1)

    assert st.confirmed_anomaly == "LIGHT_STUCK"

    # 6. Persistir la alerta confirmada en base de datos SQLite
    database.insert_alerta_sistema(
        semaforo_id="s1",
        ubicacion="AC 13 con CL 13",
        tipo_anomalia=st.confirmed_anomaly,
        detalle="Luz amarilla de despeje excedio el tiempo maximo de permanencia"
    )

    reportes = database.list_reportes()
    assert len(reportes) >= 1
    assert "LIGHT_STUCK" in reportes[0].descripcion
    assert reportes[0].ubicacion == "AC 13 con CL 13"
