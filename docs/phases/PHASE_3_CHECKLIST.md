# Checklist de Fase 3 — Datasets y datos de validación

## Etapa 1: Datasets abiertos de referencia (LISA y Bosch)

- [x] Delimitar fuentes públicas iniciales a **LISA** y **Bosch Small Traffic Lights Dataset (BSTLD)**.
- [x] Convertir anotaciones LISA CSV y Bosch YAML a clase única YOLO (`traffic_light`).
- [x] Mantener proveedores independientes y generar particiones reproducibles 70/20/10 (`seed=42`) con `data.yaml` y manifiesto.
- [x] Validar localmente ambos conjuntos: **LISA** (36,775 imágenes; 232,348 cajas) y **Bosch** (7,147 imágenes; 13,486 cajas), con 0 etiquetas inválidas.

## Etapa 2: Evolución hacia datos reales de Bogotá

- [x] Evaluar brecha de dominio de LISA y Bosch frente a semáforos reales de Bogotá.
- [x] Construir el dataset especializado **`data/processed/bogota_augmented`** en formato YOLO de 1 clase (`traffic_light`).
- [x] Particionar **`bogota_augmented`** en 70/20/10 (`seed=42`): **315 `train` / 90 `val` / 45 `test`** (**450 imágenes totales**).
- [x] Consolidar el banco de validación continua con los **8 videos reales de Bogotá** (`data/test_videos/cctv_s1.mp4` a `cctv_s8.mp4`) y las **8 escenas históricas** (`data/history_scenes/escena_s1.png` a `escena_s8.png`).
- [x] Limpiar del repositorio assets pesados sin uso durante la auditoría de optimización.

**Estado:** ✅ Completada (datos base y conjunto especializado de Bogotá integrados en el sistema funcional)
