# Checklist de Fase 1 — Definición y preparación

## Objetivo
Definir formalmente las anomalías, establecer la secuencia vial colombiana, centralizar parámetros y preparar la estructura base del proyecto.

---

## Tareas completadas

### Documentación de anomalías y secuencia vial
- [x] Crear `ANOMALIES_DEFINITION.md` con catálogo de anomalías y umbrales.
- [x] Incorporar posteriormente la condición **`AMARILLO_INTERMITENTE`** observada en calle (`s1`, `s5`).
- [x] Crear `TRAFFIC_LIGHT_SEQUENCE.md` con el ciclo colombiano ($\text{ROJO} \to \text{AMARILLO}_{\text{prep}} \to \text{VERDE} \to \text{AMARILLO}_{\text{desp}} \to \text{ROJO}$).
- [x] Definir tabla de transiciones válidas, $\tau_{\max}$ y ventana de confirmación temporal.

### Configuración centralizada de parámetros
- [x] Crear `CONFIG_PARAMETERS.yaml` en la raíz como fuente única de parámetros.
- [x] Configurar parámetros del detector unificado (`models/optisignal_best.pt`, `input_size: 1280`).
- [x] Configurar parámetros del tracker ByteTrack / Kalman (`detector.tracker`).
- [x] Definir rangos HSV (`red`, `yellow`, `green`, `activation_threshold`, `min_roi_height`).
- [x] Configurar tiempos de secuencia vial, parámetros de anomalía y FPS de cámara (`15 FPS`).
- [x] Configurar SQLite (`./data/optisignal.db`), red vial GeoJSON y API FastAPI.

### Distribución de responsabilidades
- [x] Crear `TEAM_ROLES.md` definiendo áreas de Visión, Backend y Frontend/Integración.
- [x] Alinear responsabilidades con el flujo de validación sobre cámaras urbanas de Bogotá D.C.

---

## Notas de evolución respecto al plan inicial

1. **Parámetros vivos:** Todos los umbrales experimentales de `CONFIG_PARAMETERS.yaml` fueron recalibrados durante las pruebas con cámaras reales de Bogotá (ej. `confidence_threshold: 0.25`, `input_size: 1280`, `fps: 15`, `temporal_window_seconds: 5.5`).
2. **Validación en calle:** La verificación experimental de Fase 2 se ejecuta directamente sobre las 8 secuencias de video reales de Bogotá (`cctv_s1.mp4` a `cctv_s8.mp4`).

---

**Estado de fase:** ✅ Completada (base normativa y de configuración activa en uso)
