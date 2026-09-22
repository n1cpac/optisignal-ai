# Plan de implementación — OptiSignal-AI

## 1. Objetivo

Desarrollar un prototipo académico de visión por computador que detecte el estado de un semáforo mediante una cámara e identifique fallas visuales sin conectarse al controlador del semáforo.

El sistema debe mostrar los resultados y las alertas en una interfaz web desarrollada con Angular.

## 2. Alcance

El prototipo debe:

- Capturar video desde una cámara.
- Detectar el semáforo y sus luces.
- Identificar qué color está encendido.
- Detectar fallas básicas.
- Validar la secuencia de funcionamiento.
- Registrar alertas.
- Mostrar resultados en una aplicación Angular.
- Ejecutarse localmente mediante Docker Compose.

### Fallas que se evaluarán

- Todas las luces apagadas.
- Dos luces encendidas simultáneamente.
- Una luz encendida durante demasiado tiempo.
- Cambio incorrecto entre colores.
- Lente obstruido.
- Luz con brillo insuficiente.

## 3. Arquitectura

```text
Cámara
  → Python + OpenCV
  → Modelo YOLO
  → Clasificación de luces
  → Máquina de estados
  → FastAPI
  → SQLite
  → Angular
```

### Tecnologías

| Componente | Tecnología |
|---|---|
| Procesamiento de imágenes | Python y OpenCV |
| Detección | YOLO |
| Backend | FastAPI |
| Frontend | Angular |
| Base de datos | SQLite |
| Despliegue local | Docker Compose |
| Hardware de prueba | ESP32, LEDs y cámara |

SQLite es suficiente para el alcance académico. PostgreSQL solo sería necesario si el proyecto creciera o manejara múltiples cámaras y usuarios.

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
│   ├── images/
│   ├── labels/
│   └── videos/
└── prototype/
    └── esp32/
```

## 5. Fase 1 — Definición y preparación

### Actividades

- Definir las fallas que serán evaluadas.
- Establecer la secuencia normal del semáforo.
- Definir la duración de cada color.
- Preparar el entorno de desarrollo.
- Crear la estructura del repositorio.
- Distribuir las responsabilidades del equipo.

### Resultado

Alcance, arquitectura y responsabilidades claramente definidos.

## 6. Fase 2 — Prototipo físico

Construir un semáforo a escala para generar datos y simular fallas de forma controlada.

### Componentes

- ESP32.
- LED rojo.
- LED amarillo.
- LED verde.
- Resistencias.
- Cámara USB o cámara de computador.
- Estructura para sostener los LEDs.

### Actividades

- Programar la secuencia normal.
- Permitir la activación de fallas.
- Fijar la cámara frente al prototipo.
- Probar diferentes condiciones de iluminación.
- Grabar videos de cada escenario.

### Resultado

Prototipo físico capaz de representar funcionamiento normal y fallas.

## 7. Fase 3 — Dataset

### Fuentes

- Imágenes y videos del prototipo.
- LISA Traffic Light Dataset.
- Bosch Small Traffic Lights Dataset.
- DriveU Traffic Light Dataset.

Los datasets externos pueden utilizarse como referencia. La evaluación principal debe hacerse con imágenes del prototipo para mantener un alcance manejable.

### Clases de detección

Una alternativa sencilla es detectar el semáforo completo:

```text
traffic_light
```

Luego se divide la región detectada en tres áreas para analizar las luces roja, amarilla y verde.

Si esto no produce resultados suficientes, se pueden anotar las luces por separado:

```text
red_light
yellow_light
green_light
```

### Actividades

- Capturar imágenes del prototipo.
- Extraer fotogramas de los videos.
- Eliminar imágenes repetidas.
- Anotar las imágenes.
- Organizar los datos para YOLO.
- Separar entrenamiento, validación y pruebas.

### División sugerida

- Entrenamiento: 70 %.
- Validación: 20 %.
- Pruebas: 10 %.

### Resultado

Dataset anotado y preparado para entrenamiento.

## 8. Fase 4 — Detección con YOLO

### Actividades

- Seleccionar una versión ligera de YOLO.
- Entrenar el modelo con el dataset.
- Evaluar los resultados.
- Guardar los mejores pesos como `best.pt`.
- Probar el modelo con imágenes nuevas.
- Integrar el modelo con OpenCV.

### Métricas principales

- Precision.
- Recall.
- mAP@50.
- Tiempo de inferencia.

### Resultado

Modelo capaz de localizar el semáforo en imágenes y video.

## 9. Fase 5 — Identificación del color

Después de detectar el semáforo, el sistema debe determinar qué luz está encendida.

### Método inicial

Para cada región de luz:

1. Convertir la imagen a HSV.
2. Calcular el brillo y la saturación.
3. Detectar el color dominante.
4. Comparar los valores con umbrales.
5. Seleccionar la luz activa.

### Estados posibles

```text
RED
YELLOW
GREEN
OFF
UNKNOWN
```

`UNKNOWN` se utilizará cuando la imagen no tenga suficiente calidad o confianza.

### Resultado

Módulo que indique el estado visual actual del semáforo.

## 10. Fase 6 — Máquina de estados

La máquina de estados verificará que el semáforo siga la secuencia correcta.

### Secuencia esperada

```text
ROJO → VERDE → AMARILLO → ROJO
```

### Reglas básicas

- Solo una luz puede estar encendida.
- Los cambios deben seguir la secuencia esperada.
- Ningún color debe permanecer activo indefinidamente.
- Una anomalía debe aparecer en varios fotogramas antes de generar una alerta.
- Si no se detecta ninguna luz, debe registrarse una posible falla.

### Alertas

```text
ALL_LIGHTS_OFF
MULTIPLE_LIGHTS_ON
INVALID_TRANSITION
LIGHT_STUCK
LOW_BRIGHTNESS
OBSTRUCTED_LIGHT
```

Para simplificar el proyecto, la obstrucción y el brillo bajo pueden implementarse inicialmente mediante umbrales de brillo y porcentaje visible.

### Resultado

Módulo capaz de detectar anomalías temporales.

## 11. Fase 7 — Backend con FastAPI

El backend conectará el sistema de visión con la aplicación Angular.

### Funciones

- Procesar la cámara.
- Ejecutar el modelo.
- Consultar el estado actual.
- Registrar alertas.
- Entregar datos al frontend.

### Endpoints mínimos

```text
GET /health
GET /status
GET /alerts
GET /alerts/{id}
DELETE /alerts
```

### Ejemplo de estado

```json
{
  "current_state": "RED",
  "confidence": 0.92,
  "anomaly": false,
  "timestamp": "2026-09-22T10:30:00Z"
}
```

### Base de datos

SQLite almacenará:

- Fecha y hora.
- Estado detectado.
- Tipo de anomalía.
- Confianza.
- Ruta de la imagen de evidencia.

### Resultado

API funcional conectada con el sistema de visión y la base de datos.

## 12. Fase 8 — Frontend con Angular

Angular será utilizado para construir el panel de supervisión.

### Pantallas

#### Panel principal

- Estado actual del semáforo.
- Indicador visual rojo, amarillo o verde.
- Confianza de la detección.
- Estado del sistema.
- Última actualización.

#### Alertas

- Lista de anomalías.
- Fecha y hora.
- Tipo de falla.
- Estado observado.
- Confianza.
- Imagen de evidencia.

#### Información del sistema

- Estado de la cámara.
- Estado del backend.
- Cantidad total de alertas.
- Tiempo de funcionamiento.

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

Para simplificar, Angular consultará periódicamente el backend:

```text
GET /status
```

Se puede realizar una consulta cada uno o dos segundos. WebSockets no son necesarios para el prototipo académico.

### Resultado

Interfaz Angular que muestre el estado del semáforo y las alertas.

## 13. Fase 9 — Integración

### Flujo completo

```text
1. La cámara captura un fotograma.
2. YOLO detecta el semáforo.
3. OpenCV analiza las luces.
4. La máquina de estados valida el resultado.
5. FastAPI registra las anomalías.
6. Angular consulta la API.
7. El usuario visualiza el estado y las alertas.
```

### Actividades

- Conectar YOLO con OpenCV.
- Conectar el procesamiento con FastAPI.
- Conectar FastAPI con SQLite.
- Conectar Angular con FastAPI.
- Probar el flujo completo.

### Resultado

Sistema integrado funcionando localmente.

## 14. Fase 10 — Pruebas

### Escenarios

| Escenario | Resultado esperado |
|---|---|
| Secuencia normal | No generar alerta |
| Todas las luces apagadas | Generar `ALL_LIGHTS_OFF` |
| Dos luces encendidas | Generar `MULTIPLE_LIGHTS_ON` |
| Cambio incorrecto | Generar `INVALID_TRANSITION` |
| Luz activa demasiado tiempo | Generar `LIGHT_STUCK` |
| Brillo insuficiente | Generar `LOW_BRIGHTNESS` |
| Cámara desconectada | Mostrar error de cámara |

### Pruebas técnicas

- Probar el modelo con imágenes no utilizadas en el entrenamiento.
- Verificar los endpoints de FastAPI.
- Verificar la visualización en Angular.
- Confirmar el almacenamiento de alertas.
- Medir el tiempo de procesamiento.
- Evaluar falsos positivos y falsos negativos.

### Resultado

Prototipo validado mediante escenarios controlados.

## 15. Fase 11 — Docker

Docker permitirá ejecutar el backend y el frontend sin instalar manualmente todas sus dependencias.

### Servicios

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

SQLite puede almacenarse en un volumen del backend, por lo que no se necesita un contenedor de base de datos independiente.

### Ejecución

```bash
docker compose up --build
```

### Acceso

```text
Frontend: http://localhost:4200
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs
```

### Resultado

Sistema ejecutable localmente con Docker Compose.

## 16. Fase 12 — Documentación y presentación

### Documentación requerida

- Instalación.
- Ejecución.
- Entrenamiento del modelo.
- Arquitectura.
- Endpoints de la API.
- Escenarios de prueba.
- Resultados obtenidos.
- Limitaciones.
- Trabajo futuro.

### Demostración final

1. Iniciar el sistema.
2. Mostrar una secuencia normal.
3. Activar una falla.
4. Mostrar la detección de la anomalía.
5. Verificar la alerta en Angular.
6. Mostrar la evidencia almacenada.

## 17. Cronograma sugerido

| Semana | Actividad |
|---|---|
| 1 | Definición y arquitectura |
| 2 | Construcción del prototipo físico |
| 3 | Captura y anotación de datos |
| 4 | Entrenamiento de YOLO |
| 5 | Identificación del color |
| 6 | Máquina de estados |
| 7 | Backend con FastAPI |
| 8 | Frontend con Angular |
| 9 | Integración y Docker |
| 10 | Pruebas y documentación |

## 18. Distribución sugerida del equipo

### Integrante 1 — Visión artificial

- Dataset.
- Anotaciones.
- Entrenamiento de YOLO.
- Procesamiento con OpenCV.

### Integrante 2 — Backend y validación

- Máquina de estados.
- FastAPI.
- SQLite.
- Registro de alertas.

### Integrante 3 — Frontend e integración

- Aplicación Angular.
- Panel de supervisión.
- Integración con la API.
- Docker y documentación.

Las tareas deben revisarse conjuntamente para evitar que cada componente se desarrolle de forma aislada.

## 19. Definición de terminado

El proyecto se considera terminado cuando:

- La cámara captura el prototipo.
- YOLO detecta el semáforo.
- El sistema identifica la luz activa.
- La máquina de estados reconoce fallas básicas.
- FastAPI expone el estado y las alertas.
- SQLite conserva las alertas.
- Angular muestra el estado y el historial.
- El sistema se ejecuta con Docker Compose.
- Los escenarios de prueba están documentados.
- Existe una demostración funcional.

## 20. Limitaciones

- El sistema se validará principalmente en un entorno controlado.
- No se garantiza funcionamiento en todas las condiciones exteriores.
- La precisión dependerá del tamaño y la calidad del dataset.
- El prototipo estará diseñado inicialmente para una sola cámara.
- Los umbrales de brillo pueden requerir calibración.
- El sistema no se conectará a infraestructura vial real.

## 21. Trabajo futuro

- Probar con semáforos reales.
- Soportar varias cámaras.
- Mejorar la detección de obstrucciones.
- Incorporar usuarios y autenticación.
- Añadir notificaciones.
- Utilizar WebSockets.
- Migrar de SQLite a PostgreSQL.
- Desplegar el sistema en un dispositivo edge.
