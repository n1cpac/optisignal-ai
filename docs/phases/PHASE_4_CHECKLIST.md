# Checklist de Fase 4 — Detección con YOLO y Tracking

## Objetivo
Entrenar un detector YOLO rápido y preciso, sustituir el ensamble lento inicial por un modelo único adaptado a Bogotá D.C. e integrarlo con tracking temporal para operación estable a 15 FPS.

---

## Tareas completadas

### Etapa 1: Línea base y experimentación previa
- [x] Entrenar modelos exploratorios separados sobre LISA y Bosch (`640x640`).
- [x] Diagnosticar cuellos de botella del ensamble en CPU (~2 FPS), desvío de cajas sin tracking y pérdida de semáforos pequeños a `640px`.

### Etapa 2: Modelo unificado de Bogotá (`optisignal_best.pt`)
- [x] Preparar dataset especializado `bogota_augmented` (450 imágenes, split 315/90/45).
- [x] Entrenar **YOLOv8n** en RTX 4060 Ti con *transfer learning* (`freeze=10`, 20 épocas).
- [x] Alcanzar **99.50 % mAP@50**, **98.62 % mAP@50-95**, **99.97 % Precision** y **100.0 % Recall**.
- [x] Desactivar el ensamble en [`CONFIG_PARAMETERS.yaml`](../../CONFIG_PARAMETERS.yaml) (`ensemble: false`) y activar `models/optisignal_best.pt` a `input_size: 1280`.

### Etapa 3: Tracking, compensación de movimiento y estabilidad
- [x] Implementar filtrado geométrico anti-peatones/postes/OSD y completado de pórticos en [`backend/app/detector.py`](../../backend/app/detector.py).
- [x] Implementar compensación global de movimiento con flujo óptico **Lucas-Kanade + RANSAC** en [`backend/app/motion.py`](../../backend/app/motion.py).
- [x] Implementar **ByteTrack + Filtro de Kalman 6D + correlación NCC + numeración `#1..#N`** en [`backend/app/tracker.py`](../../backend/app/tracker.py).
- [x] Calibrar reproducción a **15 FPS** y validar los 8 casos reales de Bogotá (`cctv_s1.mp4`–`cctv_s8.mp4`) en [`backend/tests/test_bogota_pipeline.py`](../../backend/tests/test_bogota_pipeline.py).

---

## Parámetros vigentes en producción (`CONFIG_PARAMETERS.yaml`)

| Parámetro | Valor actual | Motivo técnico |
| :--- | :--- | :--- |
| `model_path` | `models/optisignal_best.pt` | Modelo único unificado adaptado a Bogotá |
| `ensemble` | `false` | Evita ejecutar 3 modelos en CPU (mejora de ~2 FPS a 15 FPS) |
| `input_size` | `1280` | Permite detectar semáforos pequeños y lejanos (`s4`, `s3`) |
| `confidence_threshold` / `low` | `0.25` / `0.12` | Asociación de doble umbral estilo ByteTrack |
| `iou_threshold` | `0.45` | Supresión de cajas duplicadas sin fusionar cabezales vecinos |
| `tracker.type` | `bytetrack` | Identidad persistente entre cuadros |
| `temporal_window_seconds` | `5.5` | Ventana temporal para confirmar `AMARILLO_INTERMITENTE` |
| `camera.fps` | `15` | Sincronía fluida de análisis y stream en CPU |

---

**Estado de fase:** ✅ Completada (en ajuste de detalles finales previos a la presentación)
