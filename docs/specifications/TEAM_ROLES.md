# Distribución de responsabilidades y arquitectura por módulos — OptiSignal-AI

## Introducción

Este documento refleja las áreas de trabajo reales del equipo (Juan Cerón, Juan Camilo Niño y Nicolás Acevedo — UMNG) tras el ajuste metodológico que **descartó el prototipo físico ESP32** y consolidó la validación sobre **8 cámaras urbanas reales de Bogotá D.C.**

---

## Área 1: Visión por Computador, Datasets y Tracking

### Alcance implementado
1. **Datasets y evolución hacia Bogotá**
   - Curaduría base de LISA (36,775 imgs) y Bosch (7,147 imgs) con partición 70/20/10.
   - Construcción del dataset **`bogota_augmented`** (450 imgs: 315 train / 90 val / 45 test) y curación de los 8 videos reales `cctv_s1.mp4`–`cctv_s8.mp4`.
2. **Detección unificada y filtrado geométrico (`detector.py`)**
   - Entrenamiento de **`models/optisignal_best.pt`** (YOLOv8n, `freeze=10`, 99.50 % mAP@50) operando a `1280px` sin ensamble lento.
   - Filtrado geométrico anti-peatones/postes/OSD, NMS estricto y completado geométrico de pórticos cantiléver.
3. **Tracking y compensación de movimiento (`tracker.py`, `motion.py`)**
   - Compensación global de movimiento con flujo óptico **Lucas-Kanade + RANSAC** (`motion.py`).
   - **ByteTrack + Filtro de Kalman 6D + correlación NCC** con límites de expansión dimensional y numeración izquierda-derecha (`#1..#N`).
4. **Clasificación cromática HSV (`classifier.py`)**
   - Columna óptica central del 75 %, rescate de *bloom* nocturno, descuento de cielo y filtro anti-sangrado (*halo bleed*).

---

## Área 2: Máquina de Estados, Backend FastAPI y Persistencia

### Alcance implementado
1. **Validación temporal y sincronización (`state_machine.py`, `monitor.py`)**
   - FSM de la secuencia vial colombiana (`ROJO -> AMARILLO_PREP -> VERDE -> AMARILLO_DESP -> ROJO`).
   - Detección de `AMARILLO_INTERMITENTE` en ventana temporal (`5.5 s`), sincronización de pórticos, estabilidad en bucle y `_alert_lock`.
2. **API REST, streaming MJPEG y georreferenciación (`main.py`, `models.py`, `ubicacion.py`, `camera.py`)**
   - Endpoints `/semaforos`, `/camaras/{id}/mjpeg`, `/reportes`, `/reportes/{id}/abrir`, `/reportes/{id}/escena`, `/reportes/envio`, `/reportes/reset`.
   - Resolución automática de cruces sobre la **Malla Vial de Bogotá** (`malla-vial-bogota.geojson`).
3. **Base de datos SQLite y pruebas (`database.py`, `backend/tests/`)**
   - Gestión de alertas automáticas, atención por reporte, historial, escenas fijas por cruce (`escena_s1..s8.png`) y **83 pruebas automatizadas**.

---

## Área 3: Frontend Angular, Integración y Documentación

### Alcance implementado
1. **Panel web de supervisión (`frontend/Semaforos 3/panel-supervision-semaforo/`)**
   - Mapa interactivo Leaflet de Bogotá con estado en vivo de `s1`–`s8`.
   - Tarjeta simplificada de alertas activas en panel izquierdo (zona, fecha/hora y descripción).
   - Vista de detalle con video MJPEG a 15 FPS y cajas numeradas `#1..#N`.
   - Formulario de reporte con selección de `tipoFalla` (`funcionamiento` o `daño`) y cabezales afectados (`semaforosAfectados`).
   - Sincronización entre `Actuales` e `Historial` con escena correspondiente y botón discreto de reset en esquina inferior izquierda.
2. **Auditoría, optimización del repositorio y documentación**
   - Eliminación de artefactos pesados no utilizados y descarte documentado de la fase de hardware ESP32.
   - Actualización de `README.md`, `COMO_EJECUTAR.txt`, `docs/phases/` y `docs/specifications/` como base para la presentación del proyecto.

---

**Nota sobre el estado del proyecto:** Funcional y verificado en pruebas técnicas; pendiente de ajustes menores y elaboración de la presentación final.
