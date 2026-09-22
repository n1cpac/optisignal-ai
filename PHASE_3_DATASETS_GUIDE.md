# Fase 3 — Datasets de referencia — OptiSignal-AI

## Introducción

Esta fase cubre la descarga, estructuración y preparación de los datasets abiertos internacionales especializados en detección de semáforos.

---

## 1. Datasets utilizados

### 1.1 LISA Traffic Light Dataset

**Descripción:** Dataset de la Universidad de California (San Diego) con secuencias de video diurnas y nocturnas de semáforos en condiciones reales de tráfico urbano.

**Características:**
- Aproximadamente 43,007 fotogramas anotados
- Variaciones lumínicas (día, noche, atardecer)
- Múltiples ángulos y distancias de captura
- Anotaciones de bounding box para cabezales semafóricos

**Descarga:** https://www.kaggle.com/datasets/mbornstein/lisa-traffic-light-dataset

---

### 1.2 Bosch Small Traffic Lights Dataset (BSTLD)

**Descripción:** Dataset de Bosch con enfoque en semáforos a escala pequeña (lejanos) en imágenes de conducción urbana.

**Características:**
- Aproximadamente 13,587 imágenes anotadas
- Semáforos a diferentes escalas y distancias
- Anotaciones de bounding box y estado de luz
- Condiciones variadas de iluminación

**Descarga:** https://hci.iwr.uni-heidelberg.de/node/6132

---

### 1.3 DriveU Traffic Light Dataset (DTLD)

**Descripción:** Dataset de la Universidad de Tuebingen con gran volumen de instancias de semáforos en contexto urbano europeo.

**Características:**
- Aproximadamente 220,000 anotaciones de semáforos
- Variedad de condiciones climáticas y lumínicas
- Anotaciones detalladas de estado de luz
- Secuencias de video continuo

**Descarga:** https://www.uni-tuebingen.de/en/faculties/faculty-of-science/departments/computer-science/chair-of-autonomous-vision/datasets/

---

## 2. Estadísticas esperadas

### Cantidad de imágenes

| Dataset | Total | Entrenamiento | Validación | Pruebas |
|---|---|---|---|---|
| LISA | 43,007 | 30,105 | 8,601 | 4,301 |
| BSTLD | 13,587 | 9,511 | 2,717 | 1,359 |
| DTLD | 220,000 | 154,000 | 44,000 | 22,000 |
| **Combinado** | **276,594** | **193,616** | **55,318** | **27,660** |

---

## 3. Proceso de descarga

### Opción 1: Descarga manual

1. **LISA:** Ir a https://www.kaggle.com/datasets/mbornstein/lisa-traffic-light-dataset
2. **BSTLD:** Ir a https://hci.iwr.uni-heidelberg.de/node/6132
3. **DTLD:** Ir a https://www.uni-tuebingen.de/...

### Opción 2: Descarga automatizada

```bash
cd data/scripts
python download_datasets.py --dataset all --output ../datasets/
```

---

## 4. Conversión a formato YOLO

```bash
python convert_to_yolo.py --dataset lisa --input ../datasets/LISA/ --output ../datasets/LISA_yolo/
python convert_to_yolo.py --dataset bstld --input ../datasets/BSTLD/ --output ../datasets/BSTLD_yolo/
python convert_to_yolo.py --dataset dtld --input ../datasets/DTLD/ --output ../datasets/DTLD_yolo/
```

---

## 5. Partición estadística

```bash
python partition_dataset.py --input ../datasets/LISA_yolo/ --output ../datasets/LISA_partitioned/ --seed 42
python partition_dataset.py --input ../datasets/BSTLD_yolo/ --output ../datasets/BSTLD_partitioned/ --seed 42
python partition_dataset.py --input ../datasets/DTLD_yolo/ --output ../datasets/DTLD_partitioned/ --seed 42
python partition_dataset.py --combine --inputs ../datasets/LISA_partitioned/ ../datasets/BSTLD_partitioned/ ../datasets/DTLD_partitioned/ --output ../datasets/combined/ --seed 42
```

---

## 6. Validación de datasets

```bash
python validate_dataset.py --input ../datasets/combined/ --output ../datasets/validation_report.txt
```

---

## 7. Próximos pasos

Una vez completada la Fase 3:

1. **Fase 4:** Entrenamiento del detector YOLO
2. **Fase 5:** Clasificación de colores
3. **Fase 10:** Pruebas y validación

---

**Fecha de creación:** 2026-09-22
**Responsable:** Integrante 1 (Visión por Computador)
