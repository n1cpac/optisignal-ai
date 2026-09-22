# Plan de implementación — OptiSignal-AI

## 1. Objetivo

Desarrollar un prototipo académico de visión por computador que detecte el estado de un semáforo mediante una cámara e identifique fallas visuales sin conectarse al controlador del semáforo.

El sistema debe mostrar los resultados y las alertas en una interfaz web desarrollada con Angular.

## 2. Alcance

El prototipo debe:

- Capturar video desde una cámara o archivo de secuencia.
- Detectar el semáforo y sus luces mediante YOLO.
- Identificar qué color está encendido mediante análisis cromático en espacio HSV.
- Validar la secuencia de funcionamiento considerando la normativa de tránsito colombiana con paso obligatorio por amarillo en ambas transiciones.
- Detectar fallas básicas operativas y visuales.
- Registrar alertas con evidencia temporal y visual.
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