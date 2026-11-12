# Especificación de la secuencia vial colombiana — OptiSignal-AI

## Introducción

Este documento define formalmente la secuencia de funcionamiento de un semáforo según la normativa de tránsito colombiana, incluyendo transiciones válidas, tiempos nominales y reglas de validación.

---

## 1. Ciclo vial colombiano

La secuencia obligatoria de un semáforo en Colombia es:

```
ROJO → AMARILLO (preparación) → VERDE → AMARILLO (despeje) → ROJO
```

### Descripción de cada fase

#### ROJO
- **Significado:** Detención obligatoria.
- **Duración nominal:** 30 a 120 segundos (configurable según la intersección).
- **Luz activa:** Lente rojo encendido, amarillo y verde apagados.
- **Transición siguiente:** AMARILLO_PREP (obligatorio).

#### AMARILLO_PREP (Amarillo de preparación)
- **Significado:** Preparación para el movimiento. Advierte que el rojo está por terminar.
- **Duración nominal:** 3 a 5 segundos (fijo según normativa).
- **Luz activa:** Lente amarillo encendido, rojo y verde apagados.
- **Transición siguiente:** VERDE (obligatorio).
- **Nota:** Este amarillo es obligatorio en la transición Rojo → Verde.

#### VERDE
- **Significado:** Movimiento permitido.
- **Duración nominal:** 20 a 90 segundos (configurable según la intersección).
- **Luz activa:** Lente verde encendido, rojo y amarillo apagados.
- **Transición siguiente:** AMARILLO_DESP (obligatorio).

#### AMARILLO_DESP (Amarillo de despeje)
- **Significado:** Despeje de la intersección. Advierte que el verde está por terminar.
- **Duración nominal:** 3 a 5 segundos (fijo según normativa).
- **Luz activa:** Lente amarillo encendido, rojo y verde apagados.
- **Transición siguiente:** ROJO (obligatorio).
- **Nota:** Este amarillo es obligatorio en la transición Verde → Rojo.

---

## 2. Diagrama de transiciones de la máquina de estados finitos (FSM)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────┐                                              │
│  │  ROJO    │                                              │
│  └────┬─────┘                                              │
│       │ (τ_rojo expirado)                                  │
│       ▼                                                     │
│  ┌──────────────────┐                                      │
│  │ AMARILLO_PREP    │                                      │
│  └────┬─────────────┘                                      │
│       │ (τ_amarillo_prep expirado)                         │
│       ▼                                                     │
│  ┌──────────┐                                              │
│  │  VERDE   │                                              │
│  └────┬─────┘                                              │
│       │ (τ_verde expirado)                                 │
│       ▼                                                     │
│  ┌──────────────────┐                                      │
│  │ AMARILLO_DESP    │                                      │
│  └────┬─────────────┘                                      │
│       │ (τ_amarillo_desp expirado)                         │
│       ▼                                                     │
│  ┌──────────┐                                              │
│  │  ROJO    │ ◄─────────────────────────────────────────┐ │
│  └──────────┘                                            │ │
│                                                           │ │
└───────────────────────────────────────────────────────────┘ │
                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Tabla de transiciones válidas

| Estado actual | Evento | Estado siguiente | Condición |
|---|---|---|---|
| ROJO | Tiempo expirado | AMARILLO_PREP | τ_rojo ≥ τ_rojo_min |
| AMARILLO_PREP | Tiempo expirado | VERDE | τ_amarillo_prep ≥ τ_amarillo_prep_min |
| VERDE | Tiempo expirado | AMARILLO_DESP | τ_verde ≥ τ_verde_min |
| AMARILLO_DESP | Tiempo expirado | ROJO | τ_amarillo_desp ≥ τ_amarillo_desp_min |
| Cualquiera | Anomalía detectada | UNKNOWN | Confianza detector < 0.5 |

### Transiciones inválidas (generan alerta INVALID_TRANSITION)

- ROJO → VERDE (sin pasar por AMARILLO_PREP)
- ROJO → AMARILLO_DESP
- ROJO → ROJO
- AMARILLO_PREP → ROJO
- AMARILLO_PREP → VERDE (si no ha expirado τ_amarillo_prep_min)
- VERDE → ROJO (sin pasar por AMARILLO_DESP)
- VERDE → AMARILLO_PREP
- VERDE → VERDE
- AMARILLO_DESP → VERDE
- AMARILLO_DESP → AMARILLO_PREP
- AMARILLO_DESP → AMARILLO_DESP
- Cualquier transición a un estado no definido

---

## 4. Tiempos nominales y máximos

### Tiempos mínimos de permanencia (τ_min)

| Estado | τ_min (segundos) | Justificación |
|---|---|---|
| ROJO | 30 | Tiempo mínimo para que los vehículos perpendiculares crucen |
| AMARILLO_PREP | 3 | Tiempo mínimo de advertencia antes de verde |
| VERDE | 20 | Tiempo mínimo para que los vehículos crucen |
| AMARILLO_DESP | 3 | Tiempo mínimo de despeje de la intersección |

### Tiempos máximos de permanencia (τ_max)

| Estado | τ_max (segundos) | Justificación |
|---|---|---|
| ROJO | 120 | Evitar congestión excesiva |
| AMARILLO_PREP | 5 | Evitar confusión del conductor |
| VERDE | 90 | Evitar congestión en dirección perpendicular |
| AMARILLO_DESP | 5 | Evitar confusión del conductor |

**Nota:** Estos valores son configurables según la intersección específica. Los valores aquí son recomendaciones estándar.

---

## 5. Reglas de validación

### Regla 1: Solo una luz activa
En operación normal, exactamente una de las tres luces (Rojo, Amarillo, Verde) debe estar encendida en cada momento.

**Violación:** Genera alerta `MULTIPLE_LIGHTS_ON`.

### Regla 2: Paso obligatorio por amarillo
La transición de Rojo a Verde debe incluir obligatoriamente la fase AMARILLO_PREP.
La transición de Verde a Rojo debe incluir obligatoriamente la fase AMARILLO_DESP.

**Violación:** Genera alerta `INVALID_TRANSITION`.

### Regla 3: Permanencia dentro de límites
Ningún estado debe permanecer activo más tiempo que τ_max.

**Violación:** Genera alerta `LIGHT_STUCK`.

### Regla 4: Consistencia temporal
La duración de cada fase debe ser al menos τ_min para evitar transiciones demasiado rápidas.

**Violación:** Genera alerta `INVALID_TRANSITION`.

### Regla 5: Detección de apagón
Si ninguna luz está activa durante más de N fotogramas, se genera alerta `ALL_LIGHTS_OFF`.

**Violación:** Genera alerta `ALL_LIGHTS_OFF`.

---

## 6. Ventana de confirmación temporal

Para evitar falsas alarmas por parpadeo transitorio o ruido en la detección, toda anomalía debe persistir durante al menos **N = 8 fotogramas consecutivos** antes de ser registrada en la base de datos.

### Cálculo de tiempo real

A una frecuencia de captura de **30 FPS** (fotogramas por segundo):

```
Tiempo de confirmación = N / FPS = 8 / 30 ≈ 0.27 segundos
```

A una frecuencia de captura de **60 FPS**:

```
Tiempo de confirmación = N / FPS = 8 / 60 ≈ 0.13 segundos
```

### Implementación en la FSM

```python
if anomaly_detected:
    anomaly_counter += 1
    if anomaly_counter >= N:
        # Registrar anomalía en base de datos
        log_anomaly(anomaly_type, timestamp, evidence_frame)
        anomaly_counter = 0
else:
    anomaly_counter = 0
```

---

## 7. Estados especiales

### UNKNOWN
Estado transitorio cuando:
- La confianza del detector YOLO cae por debajo de 0.5.
- La calidad del fotograma es insuficiente para clasificación.
- Se está recuperando de una pérdida de señal.

**Acción:** No se emiten alertas en este estado. Se espera a recuperar visibilidad.

### STARTUP
Estado inicial del sistema durante los primeros N fotogramas.

**Acción:** Se ignoran anomalías durante este período para evitar falsas alarmas al iniciar.

---

## 8. Ejemplo de ciclo completo

```
Tiempo (s) | Estado | Luz activa | Duración | Evento
-----------|--------|------------|----------|--------
0-45       | ROJO   | Rojo       | 45 s     | Normal
45-48      | AMARILLO_PREP | Amarillo | 3 s | Transición válida
48-75      | VERDE  | Verde      | 27 s     | Normal
75-78      | AMARILLO_DESP | Amarillo | 3 s | Transición válida
78-123     | ROJO   | Rojo       | 45 s     | Normal (ciclo se repite)
```

---

## 9. Notas normativas

1. **Normativa colombiana:** La secuencia Rojo → Amarillo → Verde → Amarillo → Rojo es obligatoria según el Código Nacional de Tránsito Terrestre (Ley 769 de 2002).

2. **Amarillo obligatorio:** El paso por amarillo en ambas transiciones (Rojo→Verde y Verde→Rojo) es un requisito legal, no una opción.

3. **Tiempos configurables:** Los tiempos específicos (τ_min, τ_max) pueden variar según la intersección y deben ser configurados por el operador municipal.

4. **Auditoría externa:** Este sistema realiza una auditoría visual externa del semáforo y no reemplaza los protocolos de seguridad del controlador de tráfico.
