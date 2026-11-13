# OptiSignal-AI

Sistema de visión por computador para la auditoría óptica autónoma y supervisión multi-cámara de semáforos viales en **Bogotá D.C.** mediante inspección externa (*caja negra*).

**Proyecto de curso — Visión por Computador** · Universidad Militar Nueva Granada (UMNG)  
**Autores:** Juan Cerón · Juan Camilo Niño · Nicolás Acevedo

> **Estado actual:** **Funcional — en etapa de ajuste de detalles finales (previo a presentación y cierre).**  
> El pipeline está validado directamente sobre **8 secuencias reales de intersecciones viales de Bogotá D.C.** (`s1` a `s8`).

---

## ¿Qué problema resuelve?

Los sistemas tradicionales de monitoreo semafórico supervisan únicamente parámetros eléctricos internos del controlador (consumo de corriente en los módulos LED). Eso deja un punto ciego crítico: **no garantiza que la luz sea realmente visible para los conductores y peatones** (lentes apagados o quemados en campo, deterioro del policarbonato, obstrucciones o fallas intermitentes).

**OptiSignal-AI** realiza una **auditoría óptica externa no invasiva**: analiza exclusivamente el flujo de video de cámaras urbanas sin conectarse al controlador de tráfico, identifica cada cabezal semafórico de la intersección, clasifica qué lente está activo, valida la coherencia temporal según la normativa vial colombiana y consolida alertas en un panel georreferenciado.

---

## Cómo funciona el pipeline de visión

```text
Video CCTV (15 FPS)
   │
   ▼
[1. Detector YOLO Unificado] ──► Filtrado geométrico (anti-peatones/postes/OSD)
   │                             + completado de pórticos cantiléver
   ▼
[2. Compensación de Movimiento] ─► Flujo óptico Lucas-Kanade + RANSAC (motion.py)
   │
   ▼
[3. Tracking ByteTrack + Kalman] ─► Kalman 6D + matching IoU/centro + plantilla NCC
   │                                + numeración espacial #1..#N (izq. -> der.)
   ▼
[4. Clasificador HSV Robusto] ───► Columna central (75%), rescate bloom LED,
   │                                descuento de cielo y filtro halo bleed
   ▼
[5. Consenso Temporal & FSM] ────► Ventana 5.5 s, AMARILLO_INTERMITENTE,
   │                                sincronización de pórtico y ciclo colombiano
   ▼
[6. FastAPI + SQLite + Angular] ─► Mapa Malla Vial Bogotá, MJPEG en vivo,
                                   alertas deduplicadas y reporte por cabezal
```

### Etapas del procesamiento en detalle

1. **Captura multi-cámara a 15 FPS (`camera.py`, `monitor.py`)**
   - Gestiona las **8 intersecciones de Bogotá (`s1` a `s8`)** a **15 FPS** (límite ajustado para evitar retrasos de cola y mantener sincronía precisa entre fotograma y bounding box en CPU).
   - Prioriza en tiempo real la cámara que el operador está viendo por streaming MJPEG (`/camaras/{id}/mjpeg`), mientras actualiza en segundo plano el resto de intersecciones por barrido *round-robin*.

2. **Detección espacial con modelo unificado (`detector.py`, `models/optisignal_best.pt`)**
   - Utiliza un **único detector YOLOv8n (`optisignal_best.pt`)** optimizado para el contexto de Bogotá con resolución de entrada **`1280px`** para no perder semáforos pequeños o lejanos.
   - Incorpora **filtrado geométrico** (`Detector._is_valid_box`) por relación de aspecto (`1.35 <= h/w <= 4.35`), dimensiones mínimas y bandas de posición para descartar peatones cercanos, recortes de postes y texto OSD, además de completado geométrico cuando un pórtico o brazo cantiléver pierde confianza en un cabezal secundario.

3. **Tracking multi-objeto y compensación global de movimiento (`tracker.py`, `motion.py`)**
   - **Compensación global de cámara (`motion.py`)**: calcula puntos característicos (`goodFeaturesToTrack`), flujo óptico piramidal bidireccional (**Lucas-Kanade**) y una transformación afín parcial robusta con **RANSAC** (`cv2.estimateAffinePartial2D`), desplazando y escalando las cajas cuando la cámara panes o vibra sin dejar que vehículos o peatones arrastren la estimación.
   - **ByteTrack + Kalman 6D + plantilla NCC (`tracker.py`)**: asocia detecciones de alta (`>= 0.25`) y baja (`>= 0.12`) confianza mediante IoU y distancia normalizada de centros, estabiliza posición y dimensiones con un **Filtro de Kalman de 6 estados** (`cx, cy, w, h, vx, vy`) con límites contra expansión súbita por intrusos, re-ancla por **correlación cruzada normalizada (NCC)** y asigna identidades estables numeradas de izquierda a derecha (`#1, #2, #3...`).

4. **Clasificación cromática robusta en HSV (`classifier.py`)**
   - Recorta la región de interés al **75 % central horizontal** para excluir viseras y estructuras metálicas amarillas de los postes.
   - Divide esa columna óptica en tres tercios verticales (**rojo**, **amarillo**, **verde**), rescata el núcleo blanco saturado cuando hay *bloom* nocturno, descuenta píxeles de cielo azul o nublado de fondo y filtra el sangrado óptico (*halo bleed*) entre lentes vecinos.

5. **Consenso temporal, parpadeo amarillo y FSM (`state_machine.py`, `tracker.py`, `monitor.py`)**
   - Valida el ciclo normativo colombiano:
     $$\text{ROJO} \longrightarrow \text{AMARILLO}_{\text{prep}} \longrightarrow \text{VERDE} \longrightarrow \text{AMARILLO}_{\text{desp}} \longrightarrow \text{ROJO}$$
   - Mantiene una **ventana deslizante temporal de `5.5 s`** por cabezal para distinguir entre un apagado total real (**`ALL_LIGHTS_OFF`**) y un parpadeo preventivo continuo en amarillo (**`AMARILLO_INTERMITENTE`**).
   - Incluye **sincronización entre cabezales de un mismo pórtico** (`_synchronize_gantry_tracks`), preservación de estado al reiniciar el bucle del video (`on_video_loop`) e histéresis ante caídas breves de confianza para evitar falsas alertas al arrancar o reiniciar la base de datos.

6. **Backend FastAPI, SQLite y Panel Web Angular (`main.py`, `database.py`, `ubicacion.py`)**
   - Georreferencia intersecciones sobre el archivo vectorial oficial de la **Malla Vial de Bogotá** (`malla-vial-bogota.geojson`).
   - Deduplica alertas automáticas por huella de escena (`scene_signature`) y bloquea concurrencia con `_alert_lock` al consultar o reiniciar alertas (`POST /reportes/reset`).
   - El panel web Angular muestra el mapa interactivo, streaming MJPEG con cajas numeradas `#1..#N`, lista simplificada de alertas activas (zona, fecha/hora y falla), formulario de verificación con selección del **tipo de falla (`funcionamiento` o `daño`)** y **cabezales afectados**, historial con escena correspondiente a cada cruce y un control discreto de reinicio de base de datos en la esquina inferior izquierda.

---

## Evolución metodológica del entrenamiento y pruebas

El diseño actual es el resultado de tres iteraciones documentadas (base clave para la presentación del proyecto):

| Etapa | Enfoque | Hallazgo técnico | Solución adoptada en el sistema actual |
| :--- | :--- | :--- | :--- |
| **1. Datasets abiertos** | Línea base con **LISA** (36,775 imgs) y **Bosch** (7,147 imgs) | Semáforos con geometría y luminancia distinta al contexto bogotano; baja transferencia a pórticos locales | Base experimental para validación del flujo YOLO (`PHASE_3` / `PHASE_4`) |
| **2. Escenarios reales de Bogotá** | Curación de **8 videos CCTV de Bogotá** (`cctv_s1.mp4`–`cctv_s8.mp4`) + dataset local | Se requirió evaluar condiciones reales de calle: paneo, *bloom* nocturno, clima nublado, objetos lejanos y peatones | Construcción de **`bogota_augmented`** (450 imgs: 315 train / 90 val / 45 test) |
| **3. Pipeline unificado** | YOLOv8n (`freeze=10`) + tracking + compensación de movimiento | Detectar cuadro a cuadro sin memoria ni estabilización espacial producía saltos y pérdida de identidad | **`models/optisignal_best.pt`** (`99.5% mAP@50`, `1280px`) + **Lucas-Kanade/RANSAC** + **ByteTrack/Kalman** + **HSV anti-halo** |

---

## Casos reales de validación en Bogotá D.C. (`s1` a `s8`)

| ID | Intersección | Escenario real evaluado | Comportamiento verificado |
| :--- | :--- | :--- | :--- |
| **`s1`** | **AK 80 con AC 55 S** | Escena nocturna con parpadeo amarillo continuo | Detecta *bloom* nocturno, identifica `AMARILLO_INTERMITENTE` y emite alerta |
| **`s2`** | **CL 17 con KR 106** | Semáforo permanentemente apagado | Clasifica `apagado` y mantiene alerta estable `ALL_LIGHTS_OFF` |
| **`s3`** | **KR 92 con CL 169B** | Dos semáforos en verde con baja confianza en uno | Tracking persistente de ambos cabezales en `verde` sin falsos apagados |
| **`s4`** | **AC 26 con KR 19** | Dos semáforos pequeños y lejanos al fondo | Inferencia a `1280px` + completado geométrico detecta ambos en operación |
| **`s5`** | **KR 14 con CL 44 S** | Pórtico con 3 semáforos parpadeando en amarillo + fuerte movimiento de cámara | Compensación LK+RANSAC estabiliza los 3 cabezales como `AMARILLO_INTERMITENTE` |
| **`s6`** | **AK 7 con CL 84** | Semáforo en verde con peatón pasando a la derecha | Filtros geométricos y límite de expansión Kalman evitan capturar al peatón |
| **`s7`** | **AK 104 con AC 145** | Pórtico en rojo con paneo/vibración y tendencia a sobre-detección | NMS y tope de pórtico mantienen los 3 cabezales en `rojo` sin falso `ALL_LIGHTS_OFF` |
| **`s8`** | **AK 104 con AC 72** | Intersección multipostes en transición amarillo → rojo | Sincronización de pórtico evita falso apagado o falso amarillo intermitente |

---

## Estructura actual del repositorio

```text
optisignal-ai/
├── CONFIG_PARAMETERS.yaml       # Parámetros del detector, tracker, HSV, FSM y 8 cámaras
├── COMO_EJECUTAR.txt            # Guía rápida paso a paso para levantar backend y panel
├── README.md                    # Documentación principal del proyecto
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # API REST FastAPI + streaming MJPEG
│   │   ├── monitor.py           # Orquestación multi-cámara, sincronización de pórticos y alertas
│   │   ├── detector.py          # Inferencia YOLOv8n, filtrado geométrico y NMS
│   │   ├── tracker.py           # ByteTrack + Filtro de Kalman 6D + NCC + ventana temporal
│   │   ├── motion.py            # Compensación global de movimiento (Lucas-Kanade + RANSAC)
│   │   ├── classifier.py        # Clasificación cromática HSV (columna central, bloom, anti-halo)
│   │   ├── state_machine.py     # FSM del ciclo vial colombiano y anomalías
│   │   ├── camera.py            # Lectura de video a 15 FPS con buffer reciente
│   │   ├── ubicacion.py         # Georreferenciación en Malla Vial de Bogotá
│   │   ├── database.py          # Persistencia SQLite (alertas automáticas y reportes)
│   │   ├── models.py            # Contratos Pydantic (Semaforo, Cabezal, Reporte, EnvioReporte)
│   │   └── config.py            # Cargador de CONFIG_PARAMETERS.yaml
│   └── tests/                   # 83 pruebas unitarias e integrales de pipeline
├── data/
│   ├── optisignal.db            # Base de datos SQLite local
│   ├── test_videos/             # Videos reales de validación (cctv_s1.mp4 ... cctv_s8.mp4)
│   ├── history_scenes/          # Capturas de referencia por intersección (escena_s1..s8.png)
│   └── processed/               # Datasets particionados (lisa, bosch, bogota_augmented)
├── docs/
│   ├── phases/                  # Plan de implementación real y checklists de fases
│   ├── specifications/          # Definición de anomalías, secuencia vial, datos y roles
│   └── paper/                   # Borrador académico LaTeX (main.tex)
├── frontend/
│   └── Semaforos 3/panel-supervision-semaforo/  # Aplicación web Angular + Leaflet + Malla Vial
└── models/
    └── optisignal_best.pt       # Pesos del detector unificado YOLOv8n
```

---

## Ejecución rápida y pruebas

Consulta [`COMO_EJECUTAR.txt`](COMO_EJECUTAR.txt) para el paso a paso completo. En resumen:

1. **Backend (Terminal 1 — raíz del repo):**
   ```powershell
   $env:PYTHONPATH="backend"
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. **Panel Angular (Terminal 2):**
   ```powershell
   cd "frontend\Semaforos 3\panel-supervision-semaforo"
   npm start
   ```
3. Abrir `http://localhost:4200` en el navegador.

### Suite de verificación automatizada

```powershell
$env:PYTHONPATH="backend"
pytest backend/tests -v
```

Resultado de referencia tras los últimos ajustes de tracking y estabilidad en bucle: **`83 passed`**.

---

## Documentación técnica relacionada

- **Guía de ejecución:** [`COMO_EJECUTAR.txt`](COMO_EJECUTAR.txt)
- **Plan de implementación y bitácora por fases:** [`docs/phases/PLAN_IMPLEMENTACION.md`](docs/phases/PLAN_IMPLEMENTACION.md)
- **Datasets y evolución hacia Bogotá:** [`docs/phases/PHASE_3_DATASETS_GUIDE.md`](docs/phases/PHASE_3_DATASETS_GUIDE.md) · [`docs/specifications/DATA_PREPARATION_REPORT.md`](docs/specifications/DATA_PREPARATION_REPORT.md)
- **Entrenamiento del detector YOLO:** [`docs/phases/PHASE_4_YOLO_TRAINING.md`](docs/phases/PHASE_4_YOLO_TRAINING.md)
- **Catálogo de anomalías y secuencia vial:** [`docs/specifications/ANOMALIES_DEFINITION.md`](docs/specifications/ANOMALIES_DEFINITION.md) · [`docs/specifications/TRAFFIC_LIGHT_SEQUENCE.md`](docs/specifications/TRAFFIC_LIGHT_SEQUENCE.md)
- **Distribución de roles:** [`docs/specifications/TEAM_ROLES.md`](docs/specifications/TEAM_ROLES.md)
