# Plan de implementación — OptiSignal-AI

## 1. Objetivo

Desarrollar un prototipo de visión por computador que detecte el estado de un semáforo mediante una cámara e identifique fallas visuales sin conectarse al controlador de tráfico.

El sistema debe mostrar los resultados y las alertas en una interfaz web desarrollada con Angular.

## 2. Alcance

El prototipo debe:

- Capturar video desde una cámara o archivo de secuencia.
- Detectar el semáforo y sus luces mediante YOLO.
- Identificar qué color está encendido mediante análisis cromático en espacio HSV.
- Validar la secuencia de funcionamiento considerando la normativa de tránsito colombiana (paso obligatorio por amarillo en ambas transiciones).
- Detectar fallas visuales y temporales.
- Registrar alertas con evidencia temporal.
- Mostrar resultados en una aplicación web Angular.
- Ejecutarse localmente mediante contenedores Docker Compose.

### Fallas que se evaluarán

- Todas las luces apagadas (`ALL_LIGHTS_OFF`).
- Dos o más luces encendidas simultáneamente (`MULTIPLE_LIGHTS_ON`).
- Una luz encendida durante demasiado tiempo (`LIGHT_STUCK`).
- Cambio incorrecto o salto en la secuencia (`INVALID_TRANSITION`).
- Lente obstruido (`OBSTRUCTED_LIGHT`).
- Luz con brillo insuficiente (`LOW_BRIGHTNESS`).

## 3. Arquitectura

```text
Cámara / Video
  → Python + OpenCV
  → Modelo YOLO
  → Clasificación de luces (HSV)
  → Máquina de estados (FSM)
  → FastAPI
  → SQLite
  → Angular
```

### Tecnologías

| Componente | Tecnología |
|---|---|
| Procesamiento de imágenes | Python 3.10 y OpenCV |
| Detección de cabezal | YOLO (Ultralytics) |
| Backend | FastAPI |
| Frontend | Angular |
| Base de datos | SQLite |
| Despliegue local | Docker Compose |
| Hardware de prueba | ESP32, LEDs y cámara USB |

SQLite es suficiente para el alcance del prototipo. PostgreSQL solo sería necesario si el proyecto creciera o manejara múltiples intersecciones y flujos concurrentes.

## 4. Estructura sugerida

```text
optisignal-ai/
├── README.md
├── PLAN_IMPLEMENTACION.md
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── camera.py
│   │   ├── detector.py
│   │   ├── classifier.py
│   │   ├── state_machine.py
│   │   ├── database.py
│   │   └── models.py
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   └── src/
├── models/
│   └── best.pt
├── data/
│   ├── datasets/        # LISA, BSTLD, DTLD particionados
│   └── test_videos/     # Secuencias de video de prueba y fallas
└── prototype/
    └── esp32/           # Firmware de prueba y simulación de fallas
```

## 5. Fase 1 — Definición y preparación

### Actividades

- Definir formalmente las anomalías que serán evaluadas.
- Establecer la secuencia normal del semáforo basada en el ciclo vial colombiano:
  $$\text{ROJO} \longrightarrow \text{AMARILLO}_{\text{prep}} \longrightarrow \text{VERDE} \longrightarrow \text{AMARILLO}_{\text{desp}} \longrightarrow \text{ROJO}$$
- Definir los rangos de temporización nominales y de umbral máximo de permanencia ($\tau_{\max}$).
- Preparar el entorno de desarrollo y dependencias (Python, PyTorch, OpenCV).
- Crear la estructura del repositorio de código.
- Distribuir las responsabilidades del equipo de trabajo.

### Resultado

Alcance, arquitectura, lógica normativa y responsabilidades claramente definidos.

## 6. Fase 2 — Prototipo físico para pruebas

Construir un semáforo a escala como banco de pruebas experimental para simular conmutación normal y fallas de forma controlada en laboratorio.

### Componentes

- ESP32.
- Diodos LED de alta luminosidad (rojo, amarillo, verde).
- Resistencias de protección.
- Cámara USB o cámara web de pruebas.
- Estructura para sostener los LEDs alineados verticalmente.

### Actividades

- Programar el microcontrolador con la secuencia normal colombiana.
- Implementar comandos vía puerto serial o pulsadores para inyectar fallas intencionales (apagado súbito, encendido simultáneo de luces, omisión de amarillo).
- Probar condiciones de visibilidad bajo diferentes niveles de luz ambiental.

### Resultado

Dispositivo físico de laboratorio capaz de reproducir secuencias normales y fallas controladas para la fase de validación.

## 7. Fase 3 — Datasets de referencia

El entrenamiento y la evaluación del detector se realizan exclusivamente a partir de las bases de datos abiertas internacionales especializadas en semaforización.

### Fuentes utilizadas

- **LISA Traffic Light Dataset:** Secuencias diurnas y nocturnas con variaciones lumínicas.
- **Bosch Small Traffic Lights Dataset (BSTLD):** Anotaciones de semáforos a escala pequeña.
- **DriveU Traffic Light Dataset (DTLD):** Gran volumen de instancias urbanas con transiciones.

### Clases y partición

Se entrena el detector para localizar la caja/cabezal del semáforo:

```text
traffic_light
```

La segmentación interna de las tres luces se resuelve geométricamente dentro del bounding box mediante división por tercios verticales.

### Actividades

- Descargar y estructurar los subconjuntos representativos de LISA, BSTLD y DTLD.
- Homogeneizar las etiquetas al formato estándar de YOLO (`.txt`).
- Realizar la partición estadística:
  - Entrenamiento: 70 %.
  - Validación: 20 %.
  - Pruebas: 10 %.

### Resultado

Conjunto de datos abierto estructurado y listo para el entrenamiento del modelo.

## 8. Fase 4 — Detección con YOLO

### Actividades

- Seleccionar una versión ligera del detector (YOLOv8n / YOLOv11n) para garantizar inferencia en tiempo real en CPU.
- Entrenar el modelo utilizando transferencia de aprendizaje (*transfer learning*) sobre el conjunto preparado.
- Evaluar métricas de rendimiento (Precision, Recall, mAP@50).
- Exportar los pesos óptimos a `models/best.pt`.
- Probar la inferencia sobre secuencias de video continuo acoplándolo con OpenCV.

### Métricas principales

- Precision.
- Recall.
- mAP@50 $\ge 90\%$.
- Tiempo de inferencia $< 35$ ms por cuadro.

### Resultado

Modelo capaz de localizar con precisión el cabezal semafórico en imágenes y video en tiempo real.

## 9. Fase 5 — Identificación del color

Una vez obtenida la ROI del semáforo con altura $h$ y ancho $w$, se determina qué luz se encuentra activa.

### Método de análisis

1. Particionar la ROI en tres zonas verticales proporcionales:
   - Superior ($0$ a $h/3$): Lente Rojo.
   - Central ($h/3$ a $2h/3$): Lente Amarillo.
   - Inferior ($2h/3$ a $h$): Lente Verde.
2. Convertir cada subregión al espacio de color HSV.
3. Aplicar máscaras de umbralización cromática ($H$) restringidas por saturación ($S \ge S_{\min}$) y brillo ($V \ge V_{\min}$).
4. Calcular el porcentaje de píxeles encendidos respecto al área del lente.
5. Determinar el estado si supera el umbral de activación $\theta_{\text{act}}$.

### Estados reconocidos

```text
RED
YELLOW
GREEN
OFF
UNKNOWN
```

`UNKNOWN` se utilizará cuando la calidad del cuadro sea insuficiente o la confianza de detección no supere el mínimo configurado.

### Resultado

Módulo algorítmico que clasifica en cada fotograma el estado de los tres lentes.

## 10. Fase 6 — Máquina de estados finitos (FSM)

La máquina de estados verifica la consistencia temporal y valida que se cumpla la regulación vial colombiana.

### Secuencia obligatoria

```text
ROJO → AMARILLO (preparación) → VERDE → AMARILLO (despeje) → ROJO
```

### Reglas de consistencia

- Solo una luz puede estar encendida en operación normal.
- El paso entre Rojo y Verde exige la presencia de la fase intermedia en Amarillo.
- Ningún color debe permanecer activo por más tiempo que $\tau_{\max}$.
- Para evitar falsas alarmas por parpadeo (*flickering*), una anomalía debe persistir de manera continua durante una ventana temporal mínima ($N \ge 8$ fotogramas) antes de consolidar la alerta.

### Catálogo de alertas

```text
ALL_LIGHTS_OFF        # Ninguna luz emite luminancia
MULTIPLE_LIGHTS_ON    # Dos o más luces encendidas simultáneamente
INVALID_TRANSITION    # Salto ilegal de secuencia (ej. Rojo directo a Verde)
LIGHT_STUCK           # Luz activa excediendo el tiempo límite
LOW_BRIGHTNESS        # Emisión de luminancia por debajo del umbral mínimo
OBSTRUCTED_LIGHT      # Detección de cabezal pero con lente no visible
```

### Resultado

Módulo lógico capaz de auditar la secuencia y emitir diagnósticos de anomalía temporal.

## 11. Fase 7 — Backend con FastAPI

El backend conecta el pipeline de visión artificial con la base de datos y la interfaz de usuario.

### Funciones

- Iniciar y gestionar la captura de video / cámara.
- Ejecutar el detector YOLO y el clasificador HSV.
- Alimentar la máquina de estados en cada ciclo.
- Registrar anomalías confirmadas en la base de datos SQLite.
- Exponer la información en formato JSON mediante API REST.

### Endpoints principales

```text
GET /health
GET /status
GET /alerts
GET /alerts/{id}
DELETE /alerts
```

### Formato de respuesta de estado

```json
{
  "current_state": "YELLOW",
  "phase_type": "PREPARATION",
  "confidence": 0.94,
  "anomaly_detected": false,
  "timestamp": "2026-09-22T10:30:00Z"
}
```

### Base de datos (SQLite)

Almacena los registros de anomalía:

- Identificador único (`id`).
- Fecha y hora del evento (`timestamp`).
- Tipo de anomalía detectada (`anomaly_type`).
- Estado observado (`observed_state`).
- Confianza del modelo (`confidence`).
- Ruta de almacenamiento del fotograma de evidencia (`evidence_path`).

### Resultado

API REST funcional conectada al pipeline de visión y al almacenamiento de eventos.

## 12. Fase 8 — Frontend con Angular

Desarrollo del panel de supervisión web para visualización del estado del semáforo e historial de fallas.

### Vistas principales

#### Panel principal (Dashboard)

- Estado actual del semáforo con indicador gráfico interactivo (Rojo, Amarillo, Verde).
- Métrica de confianza de la detección.
- Estado operativo del sistema (Normal / Anomalía).
- Fecha y hora de la última actualización.

#### Módulo de alertas

- Tabla histórica de anomalías registradas.
- Filtros por tipo de falla y rango de fecha.
- Modal para visualizar el fotograma de evidencia capturado al momento de la falla.

#### Información del sistema

- Estado de la fuente de video.
- Tasa de procesamiento (FPS) y consumo de recursos.
- Contador acumulado de alertas.

### Componentes sugeridos

```text
src/app/
├── core/
│   └── services/
│       └── api.service.ts
├── features/
│   ├── dashboard/
│   ├── alerts/
│   └── system-status/
├── shared/
│   └── components/
│       ├── traffic-light/
│       └── alert-card/
└── app.routes.ts
```

### Comunicación

El frontend Angular consulta periódicamente el endpoint `/status` del backend mediante peticiones HTTP a intervalos regulares (1 a 2 segundos), garantizando una sincronización continua sin complejidad innecesaria.

### Resultado

Interfaz gráfica web operativa para la monitorización de la intersección.

## 13. Fase 9 — Integración del sistema

### Flujo integral

```text
1. Captura de fotograma desde la fuente de video.
2. Inferencia de YOLO para localizar el semáforo.
3. OpenCV aísla las tres ROIs y extrae el estado cromático en HSV.
4. La máquina de estados valida la transición según el ciclo colombiano.
5. Si ocurre una anomalía sostenida, FastAPI almacena el evento en SQLite.
6. Angular consulta la API REST.
7. El usuario supervisa el estado y revisa las alertas en pantalla.
```

### Actividades

- Integrar la salida de YOLO con las funciones de recorte de OpenCV.
- Conectar la máquina de estados con el gestor de persistencia en FastAPI.
- Conectar los servicios de Angular con la API de FastAPI.
- Realizar pruebas de extremo a extremo (*end-to-end*).

### Resultado

Sistema completamente integrado y funcional en entorno local.

## 14. Fase 10 — Pruebas y validación

### Matriz de casos de prueba

| Escenario de prueba | Condición inducida | Resultado esperado |
|---|---|---|
| Ciclo normal | Rojo → Amarillo → Verde → Amarillo → Rojo | Sin alertas, estado nominal |
| Apagón de intersección | Leds sin emisión sostenida | Alerta `ALL_LIGHTS_OFF` |
| Falla de conflicto | Encendido de Rojo y Verde al tiempo | Alerta `MULTIPLE_LIGHTS_ON` |
| Salto no reglamentario | Transición directa de Rojo a Verde sin pasar por Amarillo | Alerta `INVALID_TRANSITION` |
| Semáforo trabado | Un estado activo superior a $\tau_{\max}$ | Alerta `LIGHT_STUCK` |
| Pérdida de luminancia | Atenuación severa de la intensidad del LED | Alerta `LOW_BRIGHTNESS` |
| Desconexión de cámara | Fuente de video no disponible | Alerta de desconexión de cámara |

### Pruebas técnicas

- Medición de la tasa de acierto y matriz de confusión en la clasificación cromática.
- Evaluación de la tasa de cuadros por segundo (FPS) en CPU.
- Verificación del correcto almacenamiento y consulta de evidencias en SQLite.
- Cuantificación de falsos positivos y falsos negativos ante reflejos y transitorios.

### Resultado

Pipeline validado técnica y experimentalmente ante casos nominales y de falla.

## 15. Fase 11 — Empaquetamiento con Docker

Orquestar los servicios mediante Docker Compose para asegurar reproducibilidad y ejecución en cualquier entorno sin requerir instalación manual de librerías.

### Estructura de servicios

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "4200:80"
    depends_on:
      - backend
```

### Ejecución del entorno

```bash
docker compose up --build
```

### URLs de acceso

```text
Frontend: http://localhost:4200
Backend:  http://localhost:8000
API Docs: http://localhost:8000/docs
```

### Resultado

Sistema ejecutable y desplegable de forma automatizada con Docker Compose.

## 16. Fase 12 — Documentación y presentación

### Documentación requerida

- Guía de instalación y dependencias.
- Procedimiento para ejecución local y vía Docker.
- Metodología de entrenamiento y descarga de los datasets abiertos.
- Especificación técnica de la API REST (Swagger/OpenAPI).
- Reporte formal con métricas de rendimiento, tiempos de inferencia y tasa de detección de anomalías.
- Conclusiones y directrices de trabajo futuro.

### Protocolo de demostración

1. Inicialización de los servicios.
2. Procesamiento de secuencias normales evidenciando la secuencia con transiciones en amarillo.
3. Inyección o reproducción de eventos de falla controlados.
4. Demostración en vivo de la detección y disparo de la alerta correspondiente.
5. Inspección del panel web en Angular con la alerta y la evidencia fotográfica.

## 17. Cronograma general de trabajo

| Semana | Actividad |
|---|---|
| 1 | Definición metodológica, arquitectura y lógica de secuencia vial |
| 2 | Preparación y partición de datasets abiertos (LISA, BSTLD, DTLD) |
| 3 | Entrenamiento y evaluación del modelo detector con YOLO |
| 4 | Desarrollo del clasificador cromático en espacio HSV con OpenCV |
| 5 | Programación de la máquina de estados finitos (FSM) con histéresis temporal |
| 6 | Desarrollo del backend en FastAPI y persistencia en SQLite |
| 7 | Desarrollo del frontend en Angular (dashboard y visualización de alertas) |
| 8 | Construcción del prototipo físico ESP32 para pruebas de laboratorio |
| 9 | Integración integral del sistema y contenedorización con Docker Compose |
| 10 | Batería de pruebas experimentales, documentación técnica y cierre |

## 18. Distribución sugerida del equipo

### Integrante 1 — Visión por computador y datasets
- Curaduría y estructuración de los datasets abiertos (LISA, BSTLD, DTLD).
- Entrenamiento y benchmarking del detector YOLO.
- Segmentación geométrica y algoritmos de color en OpenCV (HSV).

### Integrante 2 — Lógica de control y backend
- Programación de la máquina de estados finitos (FSM) y lógica secuencial.
- Desarrollo de la API REST en FastAPI.
- Gestión de base de datos SQLite y persistencia de evidencias.

### Integrante 3 — Frontend, integración y hardware de pruebas
- Desarrollo de la interfaz web en Angular.
- Integración del frontend con la API REST.
- Firmware de simulación en ESP32 para pruebas de laboratorio.
- Configuración de Docker Compose y documentación general.

## 19. Criterios de aceptación (Definición de terminado)

El proyecto se considera concluido cuando:

- El pipeline procesa secuencias de video o flujos en vivo.
- El modelo YOLO detecta con precisión la posición del cabezal semafórico.
- El clasificador en HSV determina correctamente el lente activo o el estado apagado.
- La máquina de estados detecta las fallas operativas según el ciclo vial colombiano.
- FastAPI expone los endpoints de estado y registra las alertas en SQLite con evidencia visual.
- La interfaz en Angular muestra el estado en tiempo real y el histórico de fallas.
- El sistema completo se levanta mediante `docker compose up`.
- Se dispone de pruebas experimentales documentadas que validan cada falla tipificada.

## 20. Limitaciones identificadas

- La exactitud de la detección depende de la resolución y calidad de la cámara en tomas lejanas.
- Condiciones ambientales extremas (niebla densa o deslumbramiento solar frontal directo) pueden requerir calibración específica de umbrales.
- El prototipo inicial está diseñado para auditar un cabezal semafórico por cámara.
- El sistema realiza una auditoría visual externa y no reemplaza los protocolos físicos de emergencia de un controlador municipal.

## 21. Trabajo futuro

- Incorporar seguimiento multiobjeto (MOT) para monitorear varios semáforos simultáneamente en una intersección compleja.
- Implementar comunicación mediante WebSockets para reducir la latencia de actualización en el frontend.
- Integrar algoritmos de desoclución basados en redes convolucionales para compensar obstrucciones parciales por vehículos altos.
- Migrar el almacenamiento a PostgreSQL para despliegues municipales con alta concurrencia.
- Optimizar el pipeline mediante cuantización TensorRT para su despliegue directo en hardware de borde (*Edge AI*).