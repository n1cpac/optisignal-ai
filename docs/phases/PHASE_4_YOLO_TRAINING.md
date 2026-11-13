# Fase 4 — Detección con YOLO, Tracking y Compensación de Movimiento

## 1. Evolución de la metodología de entrenamiento

### Iteración inicial (modelos separados + ensamble)
En la primera etapa se entrenaron modelos independientes sobre **LISA** (`lisa_best.pt`), **Bosch** (`bosch_best.pt`) y renders sintéticos (`blender_best.pt`) a resolución `640x640`, combinados en un ensamble de 3 modelos dentro del backend.

Al probar este enfoque sobre videos reales de Bogotá D.C. aparecieron tres cuellos de botella:
1. **Latencia severa en CPU (~2 FPS):** inferir 3 modelos en paralelo bloqueaba el streaming de las 8 cámaras.
2. **Pérdida de semáforos pequeños y falsos positivos:** la entrada de `640px` dejaba sin detectar cabezales lejanos (`s4`) y confundía peatones o postes cercanos (`s6`).
3. **Inestabilidad temporal sin tracking:** detectar cuadro a cuadro causaba saltos de tamaño/posición, desapariciones momentáneas (`s3`) y desvío de cajas cuando la cámara se movía (`s5`, `s7`).

---

## 2. Solución definitiva: Modelo unificado `optisignal_best.pt` (`1280px`)

Se consolidó un único modelo liviano especializado en el dominio local de Bogotá usando **YOLOv8n** con transferencia de aprendizaje sobre el dataset **`data/processed/bogota_augmented/partitioned/`** (450 imágenes: 315 `train` / 90 `val` / 45 `test`, `nc: 1`, `traffic_light`).

### Hardware y configuración de entrenamiento
- **Equipo de entrenamiento:** CPU AMD Ryzen 5 5500 · 16 GB RAM · GPU NVIDIA GeForce RTX 4060 Ti (8 GB VRAM).
- **Estrategia:** YOLOv8n con *transfer learning* congelando las primeras 10 capas (`freeze=10`), 20 épocas (`~1.8 min` en GPU).
- **Peso exportado en producción:** [`models/optisignal_best.pt`](../../models/optisignal_best.pt).

### Métricas obtenidas en el modelo maestro (`optisignal_best.pt`)

| Métrica | Valor | Descripción |
| :--- | :---: | :--- |
| **Precision** | **99.97 %** | Mínimos falsos positivos sobre postes o mobiliario urbano |
| **Recall** | **100.0 %** | Cobertura total de semáforos visibles, incluidos apagados |
| **mAP@50** | **99.50 %** | Precisión media con IoU 0.50 |
| **mAP@50-95** | **98.62 %** | Precisión media estricta multiescala |
| **Latencia (GPU)** | **2.4 ms/imagen** | Permite operar el pipeline completo en tiempo real (15 FPS configurados en CPU/video) |

---

## 3. Inferencia, filtrado geométrico y tracking en producción

Para resolver por completo los problemas detectados en video continuo, el detector `optisignal_best.pt` se integró en un pipeline de 4 capas dentro del backend:

1. **Inferencia unificada de alta resolución (`backend/app/detector.py`)**
   - `ensemble: false`, `model_path: models/optisignal_best.pt`, `input_size: 1280`.
   - Doble umbral: `confidence_threshold: 0.25` (detecciones altas) y `low_confidence_threshold: 0.12` (para recuperación en ByteTrack), con NMS `iou_threshold: 0.45`.
   - **Filtrado geométrico (`Detector._is_valid_box`)**: exige orientación vertical (`1.35 <= h/w <= 4.35`), tamaño mínimo (`w >= 14`, `h >= 24`) y descarta barra OSD superior, bordes de postes y peatones grandes en primer plano (`s6`, `s8`).
   - **Completado de pórticos y NMS estricto (`_nms_and_complete`)**: elimina cajas duplicadas con solapamiento vertical y reconstruye cabezales faltantes en brazos cantiléver cuando YOLO cae momentáneamente de confianza (`s3`, `s4`, `s5`).

2. **Compensación global de movimiento de cámara (`backend/app/motion.py`)**
   - Extrae esquinas en escala reducida (`SMALL_WIDTH = 640`), calcula flujo óptico piramidal bidireccional (**Lucas-Kanade**, `calcOpticalFlowPyrLK`) y estima una transformación de similitud 2D robusta con **RANSAC** (`cv2.estimateAffinePartial2D`).
   - Desplaza y reescala las cajas existentes al movimiento de la cámara antes de asociar detecciones, evitando que vehículos o peatones arrastren las cajas y eliminando el retraso visual durante paneos (`s5`, `s7`).

3. **Tracking multi-objeto ByteTrack + Filtro de Kalman 6D (`backend/app/tracker.py`)**
   - Mantiene estado `[cx, cy, w, h, vx, vy]` por cabezal mediante `KalmanBoxFilter`.
   - Limita cambios bruscos de tamaño (`max_size_change_ratio: 0.18`) y ancla el centro ante expansiones laterales anómalas para que un peatón junto al semáforo no capture la caja (`s6`).
   - Aplica **re-anclaje por correlación cruzada normalizada (NCC)** ante caídas breves de confianza sin crear cajas fantasmas en cortes de escena (`s3`).
   - Numera de manera determinista los cabezales visibles de izquierda a derecha (`#1, #2, #3...`).

4. **Ventana temporal y manejo de bucles (`tracker.py`, `monitor.py`)**
   - Evalúa los estados sobre una ventana deslizante de `5.5 s` (`temporal_window_seconds`) para distinguir `AMARILLO_INTERMITENTE` de `ALL_LIGHTS_OFF`.
   - Al reiniciar el bucle de un video (`on_video_loop`), preserva estados estables (`ever_lit`) e impide falsos `ALL_LIGHTS_OFF` o `LIGHT_STUCK` al cruzar el límite del video (`s2`, `s6`, `s8`).

---

## 4. Verificación

Toda la integración de `optisignal_best.pt` + tracking + clasificación está cubierta por [`backend/tests/test_bogota_pipeline.py`](../../backend/tests/test_bogota_pipeline.py) sobre los 8 videos reales de Bogotá (`cctv_s1.mp4` a `cctv_s8.mp4`), ejecutándose dentro de la suite completa de **83 pruebas**.
