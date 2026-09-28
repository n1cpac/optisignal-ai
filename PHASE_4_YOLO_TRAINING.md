# Fase 4 — Detección con YOLO

## Objetivo

Implementar un flujo reproducible de entrenamiento y evaluación del detector YOLO para localizar semáforos en imágenes y video. El modelo se entrena de forma independiente para LISA y Bosch, evaluando métricas de precisión (Precision, Recall, mAP@50) y exportando pesos optimizados.

---

## Hardware disponible

**Equipo local:**
- CPU: AMD Ryzen 5 5500
- RAM: 16 GB DDR4
- GPU: NVIDIA GeForce RTX 4060 Ti (8 GB VRAM)

**Entornos soportados:**
- Local (Windows/Linux/macOS) con GPU CUDA o CPU
- Google Colab (GPU Tesla T4)

---

## Estructura de datos esperada

La Fase 3 genera particiones independientes para cada dataset:

```text
data/processed/
├── lisa/
│   └── partitioned/
│       ├── images/
│       │   ├── train/     (25,742 imágenes)
│       │   ├── val/       (7,355 imágenes)
│       │   └── test/      (3,678 imágenes)
│       ├── labels/
│       │   ├── train/
│       │   ├── val/
│       │   └── test/
│       ├── data.yaml
│       └── partition_manifest.json
└── bosch/
    └── partitioned/
        ├── images/
        │   ├── train/     (5,002 imágenes)
        │   ├── val/       (1,429 imágenes)
        │   └── test/      (716 imágenes)
        ├── labels/
        │   ├── train/
        │   ├── val/
        │   └── test/
        ├── data.yaml
        └── partition_manifest.json
```

**Nota:** Las anotaciones corresponden a cajas de luz/semáforo según la fuente original. No se inventan cajas de cabezal agrupando lentes.

---

## Notebook Jupyter: `phase_4_yolo_training.ipynb`

El notebook implementa el flujo completo en 9 secciones:

### 1. Instalación de dependencias
- Detecta entorno (local vs Colab)
- Instala PyTorch, Ultralytics YOLO, OpenCV, etc.

### 2. Detección de hardware
- Identifica GPU NVIDIA y CUDA
- Fallback automático a CPU si no hay GPU
- Muestra información del sistema

### 3. Configuración de parámetros

**Parámetros editables (sin modificar código):**

```python
YOLO_MODEL = 'yolov8n'      # nano para inferencia rápida
EPOCHS = 5                  # Cambiar a 50-100 para entrenamiento real
BATCH_SIZE = 16             # Reducir si hay problemas de memoria
IMG_SIZE = 640              # Tamaño de imagen
PATIENCE = 10               # Early stopping
SEED = 42                   # Reproducibilidad
DATASETS = ['lisa', 'bosch'] # Entrenar ambos independientemente
```

**Rutas automáticas:**
- Local: Detecta raíz del proyecto desde ubicación del notebook
- Colab: Monta Google Drive en `/content/drive/MyDrive/optisignal-ai`

### 4. Validación de estructura de datos
- Verifica existencia de directorios train/val/test
- Cuenta imágenes y etiquetas
- Lee manifiestos de partición

### 5. Entrenamiento del modelo
- Carga modelo preentrenado (YOLOv8n)
- Entrena independientemente para LISA y Bosch
- Guarda pesos en `models/{dataset}_best.pt`
- Registra resultados en `results/phase_4/{dataset}/train/`

### 6. Evaluación del modelo
- Evalúa en conjunto de prueba
- Extrae métricas: Precision, Recall, mAP@50, mAP@50-95
- Guarda resultados en JSON

### 7. Visualización de resultados
- Gráficos de pérdida (train/val)
- Gráficos de mAP@50 por época
- Guarda en `results/phase_4/training_metrics.png`

### 8. Prueba de inferencia
- Ejecuta predicciones en imágenes de prueba
- Visualiza detecciones con bounding boxes
- Guarda muestras en `results/phase_4/{dataset}_inference_samples.png`

### 9. Resumen y próximos pasos
- Lista archivos generados
- Indica directorio de resultados
- Sugiere próximas fases

---

## Ejecución local

### Requisitos previos

1. **Python 3.10+** instalado
2. **Datasets procesados** en `data/processed/lisa/` y `data/processed/bosch/`
3. **Jupyter Notebook** instalado:
   ```bash
   pip install jupyter
   ```

### Pasos

1. **Navegar al directorio del proyecto:**
   ```bash
   cd optisignal-ai
   ```

2. **Instalar dependencias (opcional, el notebook lo hace):**
   ```bash
   pip install -r data/scripts/requirements_data.txt
   ```

3. **Iniciar Jupyter:**
   ```bash
   jupyter notebook
   ```

4. **Abrir el notebook:**
   - Navegar a `notebooks/phase_4_yolo_training.ipynb`
   - Hacer clic para abrir

5. **Ejecutar celdas en orden:**
   - Celda 1-2: Instalar dependencias
   - Celda 3: Detectar hardware
   - Celda 4: Configurar parámetros (editar si es necesario)
   - Celda 5: Validar datos
   - Celda 6: **Entrenar** (⚠ Toma tiempo según GPU/CPU)
   - Celda 7-9: Evaluar y visualizar

### Configuración recomendada para hardware local

**Con GPU RTX 4060 Ti (8 GB VRAM):**
```python
YOLO_MODEL = 'yolov8n'  # nano
EPOCHS = 50             # Entrenamiento completo
BATCH_SIZE = 16         # Cabe en VRAM
IMG_SIZE = 640
```

**Si hay problemas de memoria:**
```python
BATCH_SIZE = 8          # Reducir batch
IMG_SIZE = 416          # Reducir tamaño de imagen
```

---

## Ejecución en Google Colab

### Pasos

1. **Subir notebook a Google Drive:**
   - Crear carpeta `optisignal-ai` en Drive
   - Subir `notebooks/phase_4_yolo_training.ipynb`

2. **Abrir en Colab:**
   - Clic derecho en el notebook → "Open with" → "Google Colaboratory"

3. **Ejecutar celdas:**
   - El notebook detecta automáticamente Colab
   - Monta Google Drive en la celda 3
   - Resto igual que local

### Ventajas en Colab
- GPU Tesla T4 gratuita (12 GB VRAM)
- Más rápido que CPU local
- No requiere instalación local

### Limitaciones
- Sesión se cierra después de inactividad
- Archivos se pierden si no se guardan en Drive
- Velocidad variable según carga del servidor

---

## Métricas esperadas

### LISA (36,775 imágenes, 232,348 cajas)

**Configuración:**
- Épocas: 50
- Batch size: 16
- Tamaño imagen: 640x640

**Métricas esperadas (aproximadas):**
- Precision: 0.85-0.92
- Recall: 0.80-0.88
- mAP@50: 0.88-0.95
- Tiempo de inferencia: 15-25 ms/imagen (GPU)

### Bosch (7,147 imágenes, 13,486 cajas)

**Configuración:**
- Épocas: 50
- Batch size: 16
- Tamaño imagen: 640x640

**Métricas esperadas (aproximadas):**
- Precision: 0.80-0.90
- Recall: 0.75-0.85
- mAP@50: 0.82-0.92
- Tiempo de inferencia: 15-25 ms/imagen (GPU)

**Nota:** Las métricas reales dependen de:
- Calidad y variabilidad de las anotaciones
- Condiciones de iluminación en los datos
- Tamaño y resolución de las imágenes
- Hiperparámetros de entrenamiento

---

## Archivos generados

### Pesos entrenados
```text
models/
├── lisa_best.pt         # Pesos optimizados para LISA
└── bosch_best.pt        # Pesos optimizados para Bosch
```

### Resultados y métricas
```text
results/phase_4/
├── lisa/
│   ├── train/
│   │   ├── weights/
│   │   │   ├── best.pt
│   │   │   └── last.pt
│   │   ├── results.csv
│   │   └── ...
│   └── lisa_evaluation.json
├── bosch/
│   ├── train/
│   │   ├── weights/
│   │   │   ├── best.pt
│   │   │   └── last.pt
│   │   ├── results.csv
│   │   └── ...
│   └── bosch_evaluation.json
├── training_metrics.png
├── lisa_inference_samples.png
└── bosch_inference_samples.png
```

### Archivos ignorados por Git
Los directorios `models/` y `results/` están en `.gitignore` porque contienen artefactos pesados (pesos, gráficos, logs).

---

## Limitaciones y consideraciones

### Anotaciones
- Las cajas de LISA y Bosch representan instancias de luz/semáforo según la fuente original
- No se agrupan lentes para crear cajas de cabezal completo
- La división geométrica en tres lentes se realiza en Fase 5 (clasificación HSV)

### Reproducibilidad
- Seed fijo (42) asegura particiones reproducibles
- Resultados pueden variar ligeramente entre GPU/CPU por precisión numérica
- Versiones de PyTorch/CUDA pueden afectar resultados

### Rendimiento
- YOLOv8n es ligero pero menos preciso que versiones mayores
- Para mayor precisión, usar `yolov8s` o `yolov8m` (más lento)
- Tiempo de entrenamiento: 30-60 min (GPU), 2-4 horas (CPU)

### Datos de prueba
- El conjunto de prueba (10%) se reserva para evaluación final
- No se usa durante entrenamiento ni validación
- Proporciona estimación imparcial del rendimiento

---

## Próximos pasos

1. **Fase 5:** Clasificación de colores (HSV)
   - Usar ROI del semáforo detectado
   - Dividir en tres zonas (rojo, amarillo, verde)
   - Clasificar estado de cada lente

2. **Fase 6:** Máquina de estados finitos (FSM)
   - Validar secuencia según normativa colombiana
   - Detectar anomalías temporales
   - Generar alertas

3. **Fase 7:** Backend FastAPI
   - Integrar detector YOLO
   - Conectar con clasificador HSV
   - Exponer API REST

---

## Troubleshooting

### Error: "CUDA out of memory"
- Reducir `BATCH_SIZE` (16 → 8 → 4)
- Reducir `IMG_SIZE` (640 → 416 → 320)
- Usar CPU en lugar de GPU

### Error: "data.yaml not found"
- Verificar que Fase 3 completó correctamente
- Ejecutar `python data/scripts/prepare_datasets.py`

### Error: "No module named 'ultralytics'"
- Ejecutar celda 1 (instalación de dependencias)
- O instalar manualmente: `pip install ultralytics`

### Entrenamiento muy lento
- Verificar que GPU está siendo usada (celda 3)
- Reducir `EPOCHS` para pruebas rápidas
- Usar `yolov8n` en lugar de versiones mayores

---

## Referencias

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [LISA Traffic Light Dataset](https://cvrr.ucsd.edu/)
- [Bosch Small Traffic Lights Dataset](https://hci.iwr.uni-heidelberg.de/node/6132)
- [PyTorch CUDA Documentation](https://pytorch.org/get-started/locally/)

---

**Fecha de creación:** 2026-09-28
**Responsable:** Integrante 1 (Visión por Computador)
**Estado:** 🔄 Implementado, listo para ejecución
