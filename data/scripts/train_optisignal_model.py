#!/usr/bin/env python3
"""
Entrenamiento y fine-tuning del modelo unificado OptiSignal-AI para Bogotá.

Estrategia:
- Modelo base: YOLOv8 Nano (yolov8n.pt pre-entrenado en COCO).
- Congelamiento (freeze=10): Conserva los filtros convolucionales visuales universales
  (bordes, geometrías, reflectancia) y enfoca el entrenamiento en las cabezas de detección
  para infraestructura de Bogotá (semáforos verticales, postes amarillos, viseras negras, LED).
- Dataset: data/processed/bogota_augmented/partitioned/data.yaml (450 imágenes balanceadas).
- Hardware: Aceleración GPU NVIDIA RTX 4060 Ti (device=0).
- Salida final: models/optisignal_best.pt
"""

import json
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
DATA_YAML = ROOT / "data" / "processed" / "bogota_augmented" / "partitioned" / "data.yaml"
PROJECT_DIR = ROOT / "results" / "phase_4" / "optisignal_bogota"
MODELS_DIR = ROOT / "models"


def train_optisignal():
    print(f"CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Dispositivo GPU: {torch.cuda.get_device_name(0)}")

    device = "0" if torch.cuda.is_available() else "cpu"
    base_model = ROOT / "yolov8n.pt"
    if not base_model.exists():
        base_model_name = "yolov8n.pt"
    else:
        base_model_name = str(base_model)

    print(f"Cargando modelo base: {base_model_name}")
    model = YOLO(base_model_name)

    print(f"Iniciando entrenamiento con dataset: {DATA_YAML}")
    print("Configuración: 20 épocas, batch=16, imgsz=640, freeze=10, device=" + device)

    train_results = model.train(
        data=str(DATA_YAML),
        epochs=20,
        imgsz=640,
        batch=16,
        device=device,
        freeze=10,
        workers=4,
        project=str(PROJECT_DIR),
        name="train",
        exist_ok=True,
        pretrained=True,
        seed=42,
        deterministic=True,
        save=True,
        plots=True,
        verbose=True,
    )

    best_weights = PROJECT_DIR / "train" / "weights" / "best.pt"
    if not best_weights.exists():
        best_weights = PROJECT_DIR / "train" / "weights" / "last.pt"

    dest_weights = MODELS_DIR / "optisignal_best.pt"
    shutil.copy2(best_weights, dest_weights)
    print(f"\nModelo maestro exportado exitosamente a: {dest_weights}")

    # Validación formal en split de prueba (val / test)
    print("\nEjecutando validación del modelo entrenado...")
    val_model = YOLO(str(dest_weights))
    val_results = val_model.val(data=str(DATA_YAML), split="val", imgsz=640, device=device)

    metrics = {
        "model": "optisignal_best.pt",
        "base_model": "yolov8n.pt",
        "dataset": "bogota_augmented",
        "epochs": 20,
        "freeze": 10,
        "metrics": {
            "mAP50": float(val_results.box.map50),
            "mAP50-95": float(val_results.box.map),
            "precision": float(val_results.box.mp),
            "recall": float(val_results.box.mr),
        },
    }

    eval_file = ROOT / "results" / "phase_4" / "optisignal_evaluation.json"
    eval_file.parent.mkdir(parents=True, exist_ok=True)
    eval_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\nResultados de Evaluación:")
    print(f"  Precision: {metrics['metrics']['precision']:.4f}")
    print(f"  Recall:    {metrics['metrics']['recall']:.4f}")
    print(f"  mAP@50:    {metrics['metrics']['mAP50']:.4f}")
    print(f"  mAP@50-95: {metrics['metrics']['mAP50-95']:.4f}")
    print(f"Métricas guardadas en: {eval_file}")

    return metrics


if __name__ == "__main__":
    train_optisignal()
