#!/usr/bin/env python3
"""
Generador de secuencias CCTV de Bogotá para OptiSignal-AI.

Crea 8 videos MP4 (1280x720, 10 fps, 15 segundos cada uno) correspondientes a las
cámaras s1 a s8 del panel de supervisión de Bogotá:
- s1 a s5: Operación normal (secuencia vehicular colombiana con desfase de ciclo).
- s6: Falla ALL_LIGHTS_OFF (semáforo apagado / pérdida de fluido eléctrico).
- s7: Falla MULTIPLE_LIGHTS_ON (conflicto de circuitos, rojo + verde encendidos).
- s8: Falla LIGHT_STUCK / Discrepancia eléctrica (congelado en rojo permanente).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BOGOTA_REAL_DIR = ROOT / "data" / "datasets" / "bogota_real"
OUTPUT_VIDEOS_DIR = ROOT / "data" / "test_videos"

# Importar funciones de renderizado óptico del generador de dataset
import sys
sys.path.insert(0, str(ROOT / "data" / "scripts"))
from generate_bogota_dataset import apply_optical_state, clean_boxes


def render_cctv_frame(
    base_img: np.ndarray,
    boxes: List[Tuple[float, float, float, float]],
    state: str,
    cam_name: str,
    frame_idx: int,
    fps: int = 10,
) -> np.ndarray:
    """Genera un fotograma CCTV realista con estado óptico y telemetría de cámara."""
    # 1. Aplicar estado óptico a los semáforos
    frame = apply_optical_state(base_img, boxes, state)

    # 2. Redimensionar a estándar CCTV 720p (1280x720) manteniendo aspecto
    h, w = frame.shape[:2]
    target_w, target_h = 1280, 720

    # Recorte centrado a proporción 16:9
    target_aspect = 16.0 / 9.0
    current_aspect = w / h

    if current_aspect > target_aspect:
        # Imagen más ancha: recortar laterales
        new_w = int(h * target_aspect)
        start_x = (w - new_w) // 2
        frame = frame[:, start_x:start_x + new_w]
    else:
        # Imagen más alta: recortar verticalmente preservando la parte superior/media
        new_h = int(w / target_aspect)
        start_y = max(0, int((h - new_h) * 0.25))  # Mantener semáforos visibles
        if start_y + new_h > h:
            start_y = h - new_h
        frame = frame[start_y:start_y + new_h, :]

    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # 3. Micro-ruido sutil de sensor CCTV (hace que el video se sienta vivo)
    noise = np.random.normal(0, 1.8, frame.shape).astype(np.float32)
    frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 4. Telemetría de cámara (OSD - On Screen Display)
    base_time = datetime(2026, 11, 12, 10, 15, 0)
    current_time = base_time + timedelta(seconds=frame_idx / fps)
    osd_text = f"CCTV BOGOTA - {cam_name.upper()} | {current_time.strftime('%Y-%m-%d %H:%M:%S')}.{frame_idx % fps:01d}"

    # Fondo semitransparente para el texto OSD
    cv2.rectangle(frame, (18, 14), (640, 42), (15, 15, 15), -1)
    cv2.putText(
        frame,
        osd_text,
        (24, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    # Indicador de estado de señal en vivo
    cv2.circle(frame, (620, 28), 5, (30, 220, 30), -1)

    return frame


def generate_videos():
    OUTPUT_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = BOGOTA_REAL_DIR / "images"
    labels_dir = BOGOTA_REAL_DIR / "labels"

    # Definir las 8 cámaras y sus características
    cameras = [
        {
            "id": "cctv_s1",
            "name": "AC 13 con CL 13",
            "base_img": "bogota_real_04.jpg",
            "type": "NORMAL",
            "offset": 0,
        },
        {
            "id": "cctv_s2",
            "name": "AC 72 con KR 13",
            "base_img": "bogota_real_10.jpg",
            "type": "NORMAL",
            "offset": 40,
        },
        {
            "id": "cctv_s3",
            "name": "AK 7 con CL 117",
            "base_img": "bogota_real_11.jpg",
            "type": "NORMAL",
            "offset": 80,
        },
        {
            "id": "cctv_s4",
            "name": "AC 145 con KR 96",
            "base_img": "bogota_real_12.jpg",
            "type": "NORMAL",
            "offset": 20,
        },
        {
            "id": "cctv_s5",
            "name": "AC 63 con KR 103A",
            "base_img": "bogota_real_13.jpg",
            "type": "NORMAL",
            "offset": 60,
        },
        {
            "id": "cctv_s6",
            "name": "AK 97 con CL 16I",
            "base_img": "bogota_real_14.jpg",
            "type": "FALLA_ALL_OFF",
            "offset": 0,
        },
        {
            "id": "cctv_s7",
            "name": "AC 6 con TV 78C",
            "base_img": "bogota_real_07.jpg",
            "type": "FALLA_MULTIPLE",
            "offset": 0,
        },
        {
            "id": "cctv_s8",
            "name": "AK 80 con CL 59 S",
            "base_img": "bogota_real_08.jpg",
            "type": "FALLA_STUCK",
            "offset": 0,
        },
    ]

    fps = 10
    total_frames = 150  # 15 segundos a 10 fps
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    for cam in cameras:
        img_p = images_dir / cam["base_img"]
        lbl_p = labels_dir / (img_p.stem + ".txt")

        if not img_p.exists() or not lbl_p.exists():
            print(f"Alerta: {img_p} no encontrada, omitiendo {cam['id']}.")
            continue

        orig_img = cv2.imread(str(img_p))
        h, w = orig_img.shape[:2]
        raw_lines = lbl_p.read_text(encoding="utf-8").strip().splitlines()
        boxes = clean_boxes(raw_lines, w, h)

        video_path = OUTPUT_VIDEOS_DIR / f"{cam['id']}.mp4"
        writer = cv2.VideoWriter(str(video_path), fourcc, fps, (1280, 720))

        print(f"Generando video {cam['id']}.mp4 ({cam['name']}) - Tipo: {cam['type']}...")

        for f in range(total_frames):
            frame_state = "RED"
            c_type = cam["type"]

            if c_type == "NORMAL":
                # Secuencia colombiana completa (150 frames = 15s):
                # 0 a 45: ROJO (4.5s)
                # 45 a 60: AMARILLO (1.5s preparación)
                # 60 a 120: VERDE (6.0s)
                # 120 a 135: AMARILLO (1.5s despeje)
                # 135 a 150: ROJO (1.5s)
                t = (f + cam["offset"]) % total_frames
                if t < 45 or t >= 135:
                    frame_state = "RED"
                elif 45 <= t < 60:
                    frame_state = "YELLOW"
                elif 60 <= t < 120:
                    frame_state = "GREEN"
                else:
                    frame_state = "YELLOW"

            elif c_type == "FALLA_ALL_OFF":
                # Empieza en VERDE durante 3s (30 frames), luego apagón total (ALL_LIGHTS_OFF)
                if f < 30:
                    frame_state = "GREEN"
                else:
                    frame_state = "OFF"

            elif c_type == "FALLA_MULTIPLE":
                # Empieza en ROJO durante 3s (30 frames), luego corto circuito: ROJO + VERDE encendidos
                if f < 30:
                    frame_state = "RED"
                else:
                    frame_state = "MULTIPLE_RED_GREEN"

            elif c_type == "FALLA_STUCK":
                # Congelado permanentemente en ROJO (LIGHT_STUCK)
                frame_state = "RED"

            frame = render_cctv_frame(orig_img, boxes, frame_state, cam["name"], f, fps)
            writer.write(frame)

        writer.release()
        print(f"Video {cam['id']}.mp4 generado con éxito ({video_path.stat().st_size / 1024:.1f} KB).")

    print("\nTodos los videos CCTV de Bogotá han sido creados satisfactoriamente.")


if __name__ == "__main__":
    generate_videos()
