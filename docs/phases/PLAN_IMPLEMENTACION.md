# Plan de implementación y bitácora técnica — OptiSignal-AI

> **Estado del proyecto:** **Funcional — en etapa de ajuste de detalles finales (previo a presentación y cierre).**  
> **Nota metodológica clave:** Este documento conserva la hoja de ruta por fases y registra **qué cambió, qué se descartó y qué funcionó realmente en la práctica** para llevar el prototipo hasta la versión operativa actual sobre 8 intersecciones reales de Bogotá D.C.

---

## 1. Objetivo

Desarrollar un sistema de visión por computador capaz de auditar de forma autónoma y no invasiva (*caja negra*) el estado visual de los semáforos de una intersección a partir de video CCTV, estabilizar el seguimiento temporal de múltiples cabezales, detectar fallas operativas o físicas y gestionar alertas e informes en un panel web georreferenciado en Angular respaldado por FastAPI y SQLite.

---

## 2. Alcance actual implementado

El sistema en funcionamiento:

- Procesa en paralelo **8 secuencias reales de intersecciones viales de Bogotá D.C.** (`s1` a `s8`) a **15 FPS** mediante captura continua y priorización de stream activo.
- Detecta todos los cabezales visibles con un **modelo unificado YOLOv8n (`models/optisignal_best.pt`)** a **`1280px`**, aplicando filtros geométricos anti-falsos positivos y completado geométrico de pórticos cantiléver.
- Compensa el movimiento global de cámara (paneo/vibración/zoom) mediante flujo óptico **Lucas-Kanade + RANSAC** (`backend/app/motion.py`) y rastrea identidades persistentes con **ByteTrack + Filtro de Kalman 6D + correlación NCC** (`backend/app/tracker.py`).
- Numera de forma consistente cada cabezal visible de izquierda a derecha (`#1, #2, #3...`).
- Clasifica lentes activos en espacio **HSV** sobre la columna óptica central del 75 %, rescatando núcleos saturados por *bloom* nocturno, descontando píxeles de cielo y filtrando sangrado óptico (*halo bleed*).
- Evalúa la secuencia normativa colombiana ($\text{ROJO} \to \text{AMARILLO}_{\text{prep}} \to \text{VERDE} \to \text{AMARILLO}_{\text{desp}} \to \text{ROJO}$), distingue el parpadeo operativo **`AMARILLO_INTERMITENTE`** de un apagado real (`ALL_LIGHTS_OFF`), y sincroniza cabezales de un mismo pórtico.
- Expone endpoints REST + streaming MJPEG en **FastAPI**, almacena alertas y reportes en **SQLite** y permite auditar, verificar por cabezal afectado (`#1..#N`) y tipo de falla (`funcionamiento` o `daño`) desde un panel **Angular** con mapa de la Malla Vial de Bogotá.

### Fallas y condiciones evaluadas

- `ALL_LIGHTS_OFF`: apagón total sostenido cuando ningún lente emite luminancia y no existe parpadeo intermitente.
- `MULTIPLE_LIGHTS_ON`: dos o más lentes encendidos simultáneamente superando el filtro de sangrado óptico (*halo bleed*).
- `INVALID_TRANSITION`: salto no reglamentario en la secuencia colombiana (por ejemplo `ROJO -> VERDE` o `VERDE -> ROJO` sin amarillo).
- `LIGHT_STUCK`: permanencia en un color activo por encima del umbral máximo $\tau_{\max}$.
- `AMARILLO_INTERMITENTE`: condición de parpadeo indefinido en amarillo detectada por análisis sobre una ventana deslizante temporal de `5.5 s` (diferenciada de `ALL_LIGHTS_OFF` y de un amarillo sólido).
- Soporte de configuración para `LOW_BRIGHTNESS` y `OBSTRUCTED_LIGHT` en `CONFIG_PARAMETERS.yaml`.

---

## 3. Arquitectura implementada

```text
Videos CCTV Bogotá (cctv_s1..s8.mp4 @ 15 FPS)
  → CameraFeed (camera.py)
  → Detector YOLOv8n unificado 1280px + filtro geométrico + NMS (detector.py)
  → Compensación global de movimiento Lucas-Kanade + RANSAC (motion.py)
  → Tracking ByteTrack + Kalman 6D + NCC + numeración #1..#N (tracker.py)
  → Clasificación HSV 75% central + rescate bloom + anti-halo (classifier.py)
  → Ventana temporal 5.5s + FSM colombiana + sync pórtico (state_machine.py, monitor.py)
  → FastAPI + SQLite deduplicado por escena y con _alert_lock (main.py, database.py)
  → Panel Web Angular + Mapa Malla Vial Bogotá + Streaming MJPEG
```

### Stack tecnológico real

| Componente | Tecnología implementada | Notas de evolución |
|---|---|---|
| Captura y visión | Python 3.12 + OpenCV + NumPy | Flujo óptico Lucas-Kanade, RANSAC y análisis HSV |
| Detección de cabezales | YOLOv8n (`ultralytics`) — `models/optisignal_best.pt` | Un solo modelo unificado reemplaza el ensamble lento |
| Tracking | ByteTrack custom + Kalman 6D + NCC | Reemplazó la inferencia cuadro a cuadro sin memoria |
| Validación temporal | FSM en Python + ventana de `5.5 s` | Incluye detección de `AMARILLO_INTERMITENTE` |
| Backend | FastAPI + Uvicorn | Endpoints `/semaforos`, `/reportes`, `/camaras/{id}/mjpeg` |
| Base de datos | SQLite (`data/optisignal.db`) | Deduplicación por escena y bloqueo concurrente |
| Frontend | Angular + Leaflet + GeoJSON Malla Vial Bogotá | Streaming en vivo a 15 FPS y reporte por cabezal |
| Hardware / Prototipo ESP32 | **Descartado** | Reemplazado por 8 secuencias reales de Bogotá D.C. |

---

## 4. Estructura actual del repositorio

```text
optisignal-ai/
├── CONFIG_PARAMETERS.yaml       # Fuente única de configuración del sistema
├── COMO_EJECUTAR.txt            # Instrucciones de ejecución y pruebas
├── README.md                    # Descripción general, arquitectura y casos
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI + MJPEG streaming + georreferenciación
│   │   ├── monitor.py           # Bucle multi-cámara, sincronización de pórticos y alertas
│   │   ├── detector.py          # Inferencia YOLOv8n, filtrado geométrico y NMS
│   │   ├── tracker.py           # ByteTrack, Kalman 6D, NCC, ventana 5.5s y loop reanchor
│   │   ├── motion.py            # Compensación global de movimiento (Lucas-Kanade + RANSAC)
│   │   ├── classifier.py        # Clasificación cromática HSV robusta
│   │   ├── state_machine.py     # Máquina de estados finitos del ciclo colombiano
│   │   ├── camera.py            # Lector de video/cámara a 15 FPS
│   │   ├── ubicacion.py         # Resolución espacial de cruces sobre Malla Vial
│   │   ├── database.py          # Esquema SQLite de alertas automáticas y reportes
│   │   ├── models.py            # Modelos Pydantic (Semaforo, Cabezal, Reporte, EnvioReporte)
│   │   └── config.py            # Carga CONFIG_PARAMETERS.yaml
│   └── tests/                   # 83 pruebas automatizadas
├── data/
│   ├── optisignal.db            # Base de datos SQLite local
│   ├── processed/               # Datasets particionados (lisa, bosch, blender, bogota_augmented)
│   ├── test_videos/             # 8 videos reales de Bogotá (cctv_s1.mp4 .. cctv_s8.mp4)
│   └── history_scenes/          # 8 escenas fijas por intersección (escena_s1 .. escena_s8.png)
├── docs/
│   ├── phases/                  # Planificación y bitácora por fases
│   ├── specifications/          # Anomalías, secuencia vial, datos y roles
│   └── paper/                   # Artículo en LaTeX
├── frontend/
│   └── Semaforos 3/panel-supervision-semaforo/  # Panel web Angular
└── models/
    └── optisignal_best.pt       # Modelo maestro unificado
```

---

## 5. Fase 1 — Definición y preparación ✅

### Qué se planeó y qué se implementó
- Se formalizaron las anomalías (`ALL_LIGHTS_OFF`, `MULTIPLE_LIGHTS_ON`, `INVALID_TRANSITION`, `LIGHT_STUCK`, además de `AMARILLO_INTERMITENTE` identificado durante la validación en calle).
- Se estableció el ciclo colombiano obligatorio (`ROJO -> AMARILLO_PREP -> VERDE -> AMARILLO_DESP -> ROJO`) y se centralizaron todos los parámetros en [`CONFIG_PARAMETERS.yaml`](../../CONFIG_PARAMETERS.yaml).
- Se estructuró el repositorio y la división modular por componentes.

---

## 6. Fase 2 — Prototipo físico para pruebas ❌ (DESCARTADA)

### Decisión metodológica
La construcción del semáforo físico a escala con **ESP32, diodos LED y cámara USB fija fue descartada totalmente**.

### Justificación técnica
- Las pruebas demostraron que los desafíos reales del problema (vibración y paneo de cámaras urbanas, objetos pequeños al fondo, peatones junto al semáforo, *bloom* nocturno de LEDs reales, luz ambiental nublada de Bogotá y semáforos parpadeando en amarillo) **no son reproducibles en un LED de protoboard**.
- Todo el esfuerzo de validación se redirigió a **8 grabaciones reales de intersecciones semaforizadas de Bogotá D.C.** (`cctv_s1.mp4` a `cctv_s8.mp4`) y sus escenas de referencia.
- Como parte de la auditoría y limpieza del repositorio se eliminaron los artefactos obsoletos no utilizados (incluyendo assets pesados de Blender y dependencias innecesarias del flujo físico).

---

## 7. Fase 3 — Datasets de referencia y evolución hacia Bogotá ✅

### Primera etapa: Datasets públicos base (LISA y Bosch)
- Se estructuraron de manera independiente **LISA** (36,775 imágenes; 232,348 cajas) y **Bosch BSTLD** (7,147 imágenes; 13,486 cajas) con particiones reproducibles 70/20/10 (`seed=42`).
- También se exploró un conjunto sintético en Blender (`data/processed/blender`).

### Evolución necesaria hacia datos locales (`bogota_augmented`)
- Al probar los modelos entrenados exclusivamente con LISA/Bosch sobre tráfico bogotano se evidenciaron pérdidas de detección en postes de pórtico, lentes con visera profunda y escenas nocturnas/nubladas propias de la ciudad.
- **Lo que funcionó:** construir el dataset **`data/processed/bogota_augmented`** con **450 imágenes etiquetadas de clase única (`traffic_light`)** particionadas en **315 `train` / 90 `val` / 45 `test`** (`seed=42`), incorporando condiciones diurnas, nocturnas, cielo nublado y casos difíciles de Bogotá.

---

## 8. Fase 4 — Detección con YOLO, Tracking y Compensación de Movimiento ✅

### Por qué falló el enfoque inicial
1. Usar un ensamble de 3 modelos en CPU volvía la reproducción inviable (~2 FPS) y desfasaba las detecciones respecto al video.
2. Ejecutar YOLO sin tracking por fotograma provocaba saltos continuos de tamaño/posición, desapariciones intermitentes (Caso 8 `s3`), falsos positivos sobre peatones a la derecha (Caso 7 `s6`) y cajas duplicadas en pórticos (Caso 1 `s7`).
3. La cámara estándar de `640px` dejaba sin detectar semáforos lejanos (Caso 6 `s4`).
4. En cámaras con fuerte paneo/movimiento (Caso 3 `s5`, Caso 1 `s7`), incluso con Kalman básico, las cajas se quedaban "atrás" del semáforo real.

### Lo que funcionó en la versión actual
- **Modelo unificado (`detector.py`)**: `models/optisignal_best.pt` (YOLOv8n con *transfer learning*, `freeze=10`, **99.50 % mAP@50**, **98.62 % mAP@50-95**), inferido a **`input_size: 1280`**, con umbrales `confidence_threshold: 0.25` y `low_confidence_threshold: 0.12`.
- **Filtrado geométrico y completado de pórticos**: `Detector._is_valid_box` descarta cajas fuera de relación de aspecto vertical (`1.35–4.35`), texto OSD superior y objetos grandes de calle como peatones; `_nms_and_complete` aplica NMS estricto y completa cabezales en pórticos cantiléver cuando uno de los brazos cae temporalmente en confianza.
- **Compensación global de cámara (`motion.py`)**: antes de asociar detecciones, `estimate_motion` extrae esquinas en escala reducida (`640px`), calcula flujo óptico piramidal bidireccional (**Lucas-Kanade**) y estima una similitud 2D con **RANSAC** (`cv2.estimateAffinePartial2D`), moviendo y reescalando todas las cajas activas junto con el paneo de la cámara sin dejar que vehículos o peatones arrastren la transformación.
- **ByteTrack + Kalman 6D + NCC (`tracker.py`)**: asocia detecciones altas y bajas, limita expansiones bruscas de ancho/alto (`max_size_change_ratio: 0.18`) para que un peatón no estire la caja, re-ancla por correlación de plantilla (NCC) cuando YOLO parpadea y numera los cabezales de izquierda a derecha (`#1, #2, #3...`).

---

## 9. Fase 5 — Identificación robusta del color en HSV ✅

### Limitaciones encontradas inicialmente
- El amarillo de los postes y viseras de Bogotá contaminaba el análisis en ROI completas.
- De noche (`s1`, `s5`), los LEDs saturan el sensor generando un núcleo blanco central rodeado de un halo del color real.
- El cielo gris/nublado de Bogotá y el sangrado óptico (*halo bleed*) entre lentes vecinos disparaban falsas clasificaciones `MULTIPLE`.

### Lo que funcionó (`backend/app/classifier.py`)
1. Se analiza únicamente la **columna óptica central (75 % central del ancho)** de la ROI.
2. Se divide verticalmente en tercios (`red`, `yellow`, `green`) y se evalúan rangos HSV calibrados en `CONFIG_PARAMETERS.yaml`.
3. **Rescate de *bloom* nocturno**: si el tercio presenta corona cromática (`base_ratio >= 0.035`), se suma el núcleo blanco sobreexpuesto (`S <= 32, V >= 238`) como parte del lente activo.
4. **Descuento de cielo**: los píxeles de cielo azul (`H 92..142`) o nublado (`S <= 23, V 160..237`) se excluyen del denominador efectivo.
5. **Filtro anti-sangrado (`_filter_halo_bleed`)**: solo reporta `MULTIPLE` cuando el segundo lente alcanza al menos el **48 %** de activación respecto al lente dominante.

---

## 10. Fase 6 — Máquina de estados finitos, ventana temporal y sincronización ✅

### Refinamientos clave sobre la FSM original
- **Detección de `AMARILLO_INTERMITENTE` (`tracker.py`)**: sobre una ventana deslizante de **`5.5 s`** (`temporal_window_seconds`), cuando se alternan lecturas `YELLOW` y `OFF` cumpliendo una fracción mínima de amarillo (`flash_min_Ratio: 0.18`) y transiciones encendidas/apagadas reales, el sistema clasifica el cabezal como `amarillo_intermitente` y emite la falla **`AMARILLO_INTERMITENTE`**, evitando clasificarlo erróneamente como `ALL_LIGHTS_OFF` (`s1`, `s5`).
- **Sincronización de pórticos (`monitor.py`)**: `_synchronize_gantry_tracks` alinea cabezales secundarios vistos en ángulo oblicuo cuando sus compañeros de pórtico ya confirmaron estado activo (`s8`), impidiendo falsas alertas por un único cabezal con baja luminancia aparente.
- **Estabilidad al reiniciar bucle y resetear BD**: `TrackedLight.on_video_loop` conserva estados confirmados sin reiniciar el historial a `UNKNOWN` bruscamente; además, si `self.ever_lit` es verdadero y no hay parpadeo amarillo, se suprimen falsos `ALL_LIGHTS_OFF` o `LIGHT_STUCK` provocados por micro-caídas de confianza al reiniciar el video (`s6`, `s8`).

---

## 11. Fase 7 — Backend con FastAPI y SQLite ✅

### Endpoints reales implementados (`backend/app/main.py`)

| Método y ruta | Función |
| :--- | :--- |
| `GET /semaforos` | Lista los 8 semáforos con ubicación, estado operativo/visual, luces detectadas y `cabezales` (`#1..#N`) |
| `GET /camaras/{semaforo_id}/mjpeg` | Stream MJPEG en vivo a 15 FPS con bounding boxes estabilizadas, numeración `#N` y estado |
| `GET /reportes` | Paginación de vistas `actuales` (alertas pendientes de hoy, 1 por semáforo) e `historial` |
| `POST /reportes/{alerta_id}/abrir` | Marca la apertura de una alerta en el panel para gestionar recordatorios |
| `GET /reportes/{reporte_id}/escena` | Devuelve la imagen fija exacta de la intersección (`data/history_scenes/escena_{id}.png`) |
| `POST /reportes/envio` | Registra la verificación del operador (`falla`, `tipoFalla`, `semaforosAfectados`, `comentario`, `destinatarios`) y atiende las alertas pendientes de ese semáforo |
| `POST /reportes/reset` | Limpia reportes en SQLite y re-evalúa alertas vivas bajo `_alert_lock` sin condiciones de carrera |

### Persistencia y deduplicación
- Cada intersección se georreferencia por nombre vial contra `malla-vial-bogota.geojson` (`ubicacion.py`) cuando no tiene coordenadas manuales.
- `Monitor` usa `scene_signature` + `_alert_lock` para emitir una alerta por escena y evitar duplicados durante reinicios de BD.

---

## 12. Fase 8 — Frontend con Angular ✅

Ubicación: `frontend/Semaforos 3/panel-supervision-semaforo/`

### Funcionalidades implementadas
- **Mapa interactivo Leaflet optimizado**: carga limpia sin assets pesados ni bloqueos al desplazarse por el mapa de Bogotá.
- **Panel izquierdo de alertas simplificado**: muestra únicamente zona, fecha/hora y descripción concisa de la alerta.
- **Vista de detalle con streaming en vivo (15 FPS)**: renderiza `/camaras/{id}/mjpeg` y muestra los cabezales numerados `#1..#N`.
- **Formulario de reporte granular**: permite reportar confirmación o fallo seleccionando **tipo de falla (`funcionamiento` o `daño`)** y marcando exactamente **qué semáforos (`#1, #2, #3...`) presentan la falla**.
- **Consistencia entre `Actuales` e `Historial`**: al enviar un reporte sobre una cámara con alerta activa, esta desaparece de `Actuales` y pasa a `Historial` asociada a la imagen correcta de su intersección (`escena_s{n}.png`).
- **Botón sutil de depuración**: botón discreto en la esquina inferior izquierda para invocar `POST /reportes/reset` y restaurar el estado de prueba.

---

## 13. Fase 9 y 10 — Integración, limpieza y validación con los 8 casos de Bogotá 🔄 (En ajuste final)

### Optimización y auditoría del repositorio
- Se ejecutó una limpieza completa del repositorio eliminando assets no utilizados, datos redundantes y código muerto que afectaban el rendimiento de carga y navegación del mapa.
- Se bajó la cadencia de video a **15 FPS** y se priorizó el procesamiento de la cámara abierta en stream para evitar latencia y colas acumuladas.

### Matriz de validación sobre casos reales (`test_bogota_pipeline.py`)

| Caso | Cámara | Condición validada | Estado actual |
| :--- | :--- | :--- | :---: |
| Caso 1 | `s7` AK 104 con AC 145 | Dos/tres cabezales en rojo sin falso `ALL_LIGHTS_OFF` y tope de 3 cajas | ✅ Pasa |
| Caso 2 | `s2` CL 17 con KR 106 | Semáforo apagado permanente mantiene `ALL_LIGHTS_OFF` estable incluso tras loop | ✅ Pasa |
| Caso 3 | `s5` KR 14 con CL 44 S | 3 semáforos en parpadeo amarillo + paneo fuerte clasificados como `AMARILLO_INTERMITENTE` | ✅ Pasa |
| Caso 4 | `s1` AK 80 con AC 55 S | Parpadeo amarillo nocturno detectado como `AMARILLO_INTERMITENTE` (no `OFF`) | ✅ Pasa |
| Caso 5 | `s8` AK 104 con AC 72 | Múltiples cabezales en transición amarillo → rojo sin falso apagado ni parpadeo | ✅ Pasa |
| Caso 6 | `s4` AC 26 con KR 19 | Semáforos pequeños y lejanos detectados consistentemente a 1280px | ✅ Pasa |
| Caso 7 | `s6` AK 7 con CL 84 | Único semáforo en verde sin capturar al peatón de la derecha | ✅ Pasa |
| Caso 8 | `s3` KR 92 con CL 169B | Dos semáforos en verde con tracking e identidad persistente | ✅ Pasa |

- **Pruebas automatizadas**: **`83 passed`** (`pytest backend/tests -v`).
- **Prueba de estrés tras reinicio de BD**: verificados 3 ciclos consecutivos de `POST /reportes/reset` con el servidor vivo; únicamente `s1`, `s2` y `s5` aparecen en `Actuales`, mientras `s6` y `s8` se mantienen `normal`.

---

## 14. Fase 11 y 12 — Pendientes previos al cierre y futura presentación

> El sistema es **plenamente funcional**, pero **no se marca aún como finalizado** porque restan detalles finales y la preparación de la sustentación.

### Pendientes antes del cierre definitivo
- [ ] Ajuste fino de detalles visuales/operativos finales detectados en revisión de demostración.
- [ ] Consolidación de métricas finales e infografías de comparación (enfoque inicial vs. pipeline final) para la **presentación del proyecto** (pendiente por elaborar).
- [ ] Empaquetamiento reproducible opcional (`docker-compose.yml` actualmente es un esqueleto base por completar si se decide distribuir en contenedores).
- [ ] Cierre editorial del borrador académico en [`docs/paper/main.tex`](../paper/main.tex).
