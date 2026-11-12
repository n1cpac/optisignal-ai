#!/usr/bin/env python3
"""
Integra los renders y escenarios de Blender al dataset de entrenamiento de YOLO.

Proceso:
1. Recopila las 20 imagenes base de Blender con sus etiquetas ground-truth de meta.csv / labels.
2. Recopila los 96 renders realistas de 'renders_escenarios' con las cajas delimitadoras de cada escena.
3. Extrae frames representativos del video real de Bogotá (test1.mp4) con su etiqueta anotada.
4. Almacena el conjunto consolidado en data/datasets/blender/ (YOLO plano).
5. Ejecuta la partición reproducible (70% train, 20% val, 10% test) en data/processed/blender/partitioned.
6. Valida la integridad del formato YOLO y genera data.yaml y partition_manifest.json.
"""

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

# Rutas principales del proyecto
ROOT = Path(__file__).resolve().parents[2]
BLENDER_DIR = ROOT / "frontend" / "smaforos blender"
TEST_VIDEOS_DIR = ROOT / "data" / "test_videos"
RAW_OUTPUT = ROOT / "data" / "datasets" / "blender"
PROCESSED_OUTPUT = ROOT / "data" / "processed" / "blender" / "partitioned"

import sys
sys.path.insert(0, str(ROOT / "data" / "scripts"))
from partition_dataset import partition
from validate_dataset import validate_dataset


def to_yolo_line(cx: float, cy: float, w: float, h: float, class_id: int = 0) -> str:
    """Retorna la línea en formato YOLO: class_id cx cy w h con coordenadas normalizadas [0, 1]."""
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    w = max(0.0, min(1.0, w))
    h = max(0.0, min(1.0, h))
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n"


def collect_blender_base() -> List[Tuple[Path, str]]:
    """Lee las 20 imagenes base de Blender y sus etiquetas de meta.csv."""
    meta_path = BLENDER_DIR / "meta.csv"
    results = []
    if not meta_path.exists():
        print(f"Aviso: {meta_path} no encontrado, omitiendo base.")
        return results

    with open(meta_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_path = BLENDER_DIR / "images" / f"{row['imagen']}.png"
            if img_path.exists():
                cx = float(row["cx"])
                cy = float(row["cy"])
                w = float(row["w"])
                h = float(row["h"])
                results.append((img_path, to_yolo_line(cx, cy, w, h)))
    return results


def collect_blender_renders() -> List[Tuple[Path, str]]:
    """
    Lee los 96 renders realistas en renders_escenarios y asigna la caja delimitadora
    correspondiente a cada una de las 24 perspectivas de escena.
    """
    renders_dir = BLENDER_DIR / "renders_escenarios"
    if not renders_dir.exists():
        print(f"Aviso: {renders_dir} no encontrado.")
        return []

    images = sorted(renders_dir.glob("*.png"))
    if not images:
        return []

    # Mapas de cajas delimitadoras normalizadas (cx, cy, w, h) para las 24 escenas de 1280x720
    # Obtenidas a partir de la geometría y detección de alta confianza de los semáforos en cada escena
    IMG_W, IMG_H = 1280.0, 720.0

    # Cajas calculadas en pixeles [x1, y1, x2, y2] por identificador de escena (01 a 24)
    pixel_boxes: Dict[str, Tuple[float, float, float, float]] = {
        "01": (618.2, 253.5, 638.6, 300.2),
        "02": (743.3, 494.4, 786.8, 602.1),
        "03": (681.6, 389.7, 704.5, 459.5),
        "04": (680.6, 391.9, 707.3, 475.2),
        "05": (625.9, 303.0, 657.2, 396.7),
        "06": (548.5, 232.2, 570.4, 283.3),
        "07": (628.2, 310.2, 655.1, 390.5),
        "08": (681.4, 388.2, 705.2, 462.3),
        "09": (626.1, 300.4, 657.4, 399.1),
        "10": (597.8, 189.9, 641.4, 264.7),
        "11": (630.3, 317.0, 651.3, 389.4),
        "12": (624.2, 290.3, 660.0, 408.8),
        "13": (622.1, 327.7, 658.9, 419.4),
        "14": (670.4, 384.9, 692.9, 452.6),
        "15": (588.2, 89.1, 614.8, 148.6),
        "16": (629.8, 315.1, 651.8, 389.4),
        "17": (627.7, 310.4, 655.5, 393.6),
        "18": (719.0, 438.4, 816.2, 609.2),
        "19": (673.8, 383.9, 695.1, 448.3),
        "20": (688.5, 415.7, 773.4, 552.4),
        "21": (704.7, 438.5, 735.3, 516.6),
        "22": (516.4, 197.3, 540.7, 253.3),
        "23": (630.1, 319.6, 650.4, 387.5),
        "24": (631.5, 325.4, 648.8, 380.2),
    }

    results = []
    for img_path in images:
        parts = img_path.stem.split("_")
        # El indice de escena es la parte numerica
        scene_id = None
        for p in parts:
            if p.isdigit() and len(p) == 2:
                scene_id = p
                break

        if scene_id and scene_id in pixel_boxes:
            x1, y1, x2, y2 = pixel_boxes[scene_id]
            cx = ((x1 + x2) / 2.0) / IMG_W
            cy = ((y1 + y2) / 2.0) / IMG_H
            w = (x2 - x1) / IMG_W
            h = (y2 - y1) / IMG_H
            results.append((img_path, to_yolo_line(cx, cy, w, h)))

    return results


def extract_bogota_frames() -> List[Tuple[Path, str]]:
    """Extrae frames clave del video real de Bogotá (test1.mp4) con su anotación verificada."""
    video_path = TEST_VIDEOS_DIR / "test1.mp4"
    if not video_path.exists():
        return []

    output_dir = RAW_OUTPUT / "bogota_frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Extraer 1 frame cada segundo (~16 frames representativos del ciclo semafórico)
    interval = int(fps)
    extracted = []

    # Bounding box del semaforo en test1.mp4: (457.7, 120.4, 466.0, 142.5) en 640x360
    # YOLO normalizado: cx=0.721658, cy=0.365137, w=0.012940, h=0.061215
    yolo_label = to_yolo_line(0.721658, 0.365137, 0.012940, 0.061215)

    frame_idx = 0
    saved_count = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % interval == 0:
            frame_filename = output_dir / f"bogota_frame_{saved_count:03d}.jpg"
            cv2.imwrite(str(frame_filename), frame)
            extracted.append((frame_filename, yolo_label))
            saved_count += 1
        frame_idx += 1
    cap.release()

    return extracted


def build_dataset() -> None:
    print("=== INTEGRACIÓN DE DATASET BLENDER Y BOGOTÁ ===")
    
    # 1. Crear directorios limpios
    images_raw = RAW_OUTPUT / "images"
    labels_raw = RAW_OUTPUT / "labels"
    images_raw.mkdir(parents=True, exist_ok=True)
    labels_raw.mkdir(parents=True, exist_ok=True)

    # 2. Recolectar datos
    blender_base = collect_blender_base()
    blender_renders = collect_blender_renders()
    bogota_frames = extract_bogota_frames()

    all_samples = blender_base + blender_renders + bogota_frames
    print(f"Total muestras recopiladas: {len(all_samples)}")
    print(f"  - Blender base (meta.csv): {len(blender_base)}")
    print(f"  - Blender renders (renders_escenarios): {len(blender_renders)}")
    print(f"  - Frames reales de Bogotá (test1.mp4): {len(bogota_frames)}")

    # 3. Guardar en RAW_OUTPUT
    for idx, (img_path, yolo_line) in enumerate(all_samples):
        dest_stem = f"sample_{idx:04d}_{img_path.stem}"
        dest_img = images_raw / f"{dest_stem}{img_path.suffix.lower()}"
        dest_lbl = labels_raw / f"{dest_stem}.txt"

        shutil.copy2(img_path, dest_img)
        dest_lbl.write_text(yolo_line, encoding="utf-8")

    print(f"\nConjunto plano consolidado en: {RAW_OUTPUT}")

    # 4. Crear particiones (70% train, 20% val, 10% test)
    if PROCESSED_OUTPUT.exists():
        shutil.rmtree(PROCESSED_OUTPUT)
    
    manifest = partition(RAW_OUTPUT, PROCESSED_OUTPUT, ratios=(0.7, 0.2, 0.1), seed=42)
    print(f"\nPartición generada en: {PROCESSED_OUTPUT}")
    print(f"  Train: {manifest['counts']['train']}")
    print(f"  Val:   {manifest['counts']['val']}")
    print(f"  Test:  {manifest['counts']['test']}")

    # 5. Validar integridad YOLO
    report = validate_dataset(str(PROCESSED_OUTPUT))
    print(f"\nEstado de validación: {report['status']}")
    print(f"Reporte de validación: {json.dumps(report, indent=2)}")

    if report["status"] != "PASS":
        raise RuntimeError("La validación del dataset falló. Revisa las etiquetas.")

    print("\n[OK] Dataset 'blender' integrado, particionado y validado con exito.")


if __name__ == "__main__":
    build_dataset()
