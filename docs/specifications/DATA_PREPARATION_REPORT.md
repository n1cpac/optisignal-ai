# Reporte de preparación de datos — OptiSignal-AI

## 1. Datasets base procesados

- **LISA procesado (`data/processed/lisa/`):** 36,775 imágenes y 232,348 cajas (`25,742 train` / `7,355 val` / `3,678 test`). Validación: `PASS`, 0 etiquetas ausentes o inválidas.
- **Bosch BSTLD procesado (`data/processed/bosch/`):** 7,147 imágenes y 13,486 cajas (`5,002 train` / `1,429 val` / `716 test`). Validación: `PASS`, 0 etiquetas ausentes o inválidas.
- **Blender (`data/processed/blender/`):** partición sintética exploratoria previa al paso definitivo a video real.

## 2. Dataset especializado de Bogotá (`bogota_augmented`)

A partir de capturas reales y aumentación enfocada en condiciones locales de iluminación, clima y pórticos de Bogotá D.C., se generó **`data/processed/bogota_augmented/partitioned/`** (manifiesto verificado con `seed=42`, partición `70/20/10`):

- **Total de imágenes:** `450`
- **Entrenamiento (`train`):** `315` imágenes
- **Validación (`val`):** `90` imágenes
- **Prueba (`test`):** `45` imágenes
- **Clase única (`data.yaml`):** `nc: 1`, `names: [traffic_light]`

## 3. Banco de validación continua (videos y escenas de historial)

- **Videos CCTV reales (`data/test_videos/`):** `cctv_s1.mp4` a `cctv_s8.mp4`, correspondientes a los 8 cruces de Bogotá configurados en [`CONFIG_PARAMETERS.yaml`](../../CONFIG_PARAMETERS.yaml) y verificados automáticamente en [`backend/tests/test_bogota_pipeline.py`](../../backend/tests/test_bogota_pipeline.py).
- **Escenas de historial (`data/history_scenes/`):** `escena_s1.png` a `escena_s8.png`, empleadas por `GET /reportes/{id}/escena` para mostrar exactamente la intersección asociada a cada reporte.

## Resultado

La evolución desde datasets genéricos (LISA/Bosch) y escenarios sintéticos hacia `bogota_augmented` + 8 videos reales permitió entrenar un detector único rápido (`models/optisignal_best.pt`) y descartar definitivamente la fase de prototipo físico.
