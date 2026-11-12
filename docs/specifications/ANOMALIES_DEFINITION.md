# Definición formal de anomalías — OptiSignal-AI

## Introducción

Este documento especifica las seis anomalías que el sistema OptiSignal-AI detectará y clasificará. Cada anomalía incluye su descripción técnica, condiciones de detección, umbrales y ejemplos.

---

## 1. ALL_LIGHTS_OFF (Todas las luces apagadas)

### Descripción
Ninguna de las tres luces (Rojo, Amarillo, Verde) emite luminancia detectable. El semáforo está completamente apagado o desconectado.

### Condiciones de detección
- El detector YOLO localiza el cabezal del semáforo (confianza ≥ 0.5).
- En las tres ROIs (superior, central, inferior), el porcentaje de píxeles encendidos es < θ_act (umbral de activación).
- Esta condición persiste durante ≥ N fotogramas (ventana de confirmación).

### Umbrales
- Confianza mínima del detector: 0.5
- Porcentaje de píxeles encendidos por lente: < 5% (θ_act = 0.05)
- Ventana de confirmación: N ≥ 8 fotogramas (≈ 0.27 segundos a 30 FPS)

### Impacto
- **Severidad:** Crítica
- **Causa probable:** Falla de alimentación, desconexión de LEDs, fusible quemado.
- **Acción recomendada:** Alerta inmediata al operador, revisión de fuente de poder.

---

## 2. MULTIPLE_LIGHTS_ON (Dos o más luces encendidas simultáneamente)

### Descripción
Dos o más lentes están emitiendo luz simultáneamente en un estado que no es válido según la secuencia colombiana. Ejemplo: Rojo y Verde encendidos al mismo tiempo (conflicto de tráfico).

### Condiciones de detección
- El detector YOLO localiza el cabezal (confianza ≥ 0.5).
- Dos o más ROIs tienen porcentaje de píxeles encendidos ≥ θ_act.
- Esta condición persiste durante ≥ N fotogramas.

### Umbrales
- Confianza mínima del detector: 0.5
- Porcentaje de píxeles encendidos por lente: ≥ 5% (θ_act = 0.05)
- Ventana de confirmación: N ≥ 8 fotogramas

### Impacto
- **Severidad:** Crítica
- **Causa probable:** Falla en el controlador, cortocircuito, contacto defectuoso.
- **Acción recomendada:** Alerta inmediata, detención del tráfico, revisión de circuitería.

---

## 3. INVALID_TRANSITION (Transición no reglamentaria)

### Descripción
El semáforo realiza un cambio de estado que viola la secuencia legal colombiana. Ejemplos:
- Transición directa de Rojo a Verde sin pasar por Amarillo de preparación.
- Transición de Verde a Rojo sin pasar por Amarillo de despeje.
- Salto a un estado no permitido desde el estado actual.

### Condiciones de detección
- La máquina de estados registra una transición que no está en la tabla de transiciones válidas.
- La transición ocurre sin la presencia de la fase intermedia en Amarillo cuando es requerida.
- Se confirma durante ≥ N fotogramas.

### Umbrales
- Ventana de confirmación: N ≥ 8 fotogramas
- Tabla de transiciones válidas:
  ```
  ROJO → AMARILLO_PREP (obligatorio)
  AMARILLO_PREP → VERDE (obligatorio)
  VERDE → AMARILLO_DESP (obligatorio)
  AMARILLO_DESP → ROJO (obligatorio)
  ```

### Impacto
- **Severidad:** Crítica
- **Causa probable:** Falla del controlador de tráfico, corrupción de firmware.
- **Acción recomendada:** Alerta inmediata, revisión del controlador, posible cambio a modo manual.

---

## 4. LIGHT_STUCK (Luz atascada / Permanencia excesiva)

### Descripción
Una luz permanece encendida durante un tiempo superior al máximo permitido (τ_max). El semáforo está "congelado" en un estado.

### Condiciones de detección
- Una luz (Rojo, Amarillo o Verde) está activa (porcentaje de píxeles ≥ θ_act).
- El tiempo de permanencia en ese estado supera τ_max.
- Se confirma durante ≥ N fotogramas adicionales después de exceder τ_max.

### Umbrales
- Porcentaje de píxeles encendidos: ≥ 5% (θ_act = 0.05)
- Tiempos máximos de permanencia (τ_max):
  - Rojo: 120 segundos
  - Amarillo (preparación): 5 segundos
  - Verde: 90 segundos
  - Amarillo (despeje): 5 segundos
- Ventana de confirmación: N ≥ 8 fotogramas después de exceder τ_max

### Impacto
- **Severidad:** Alta
- **Causa probable:** Falla del controlador, sensor de tiempo defectuoso, contacto pegado.
- **Acción recomendada:** Alerta al operador, revisión del controlador, posible reinicio.

---

## 5. LOW_BRIGHTNESS (Brillo insuficiente)

### Descripción
Una luz está encendida pero con intensidad luminosa por debajo del umbral mínimo requerido. El LED está débil, atenuado o parcialmente defectuoso.

### Condiciones de detección
- El detector YOLO localiza el cabezal (confianza ≥ 0.5).
- Una luz está activa (porcentaje de píxeles ≥ θ_act).
- El valor promedio de brillo (V en HSV) en esa ROI es < V_min.
- Esta condición persiste durante ≥ N fotogramas.

### Umbrales
- Confianza mínima del detector: 0.5
- Porcentaje de píxeles encendidos: ≥ 5% (θ_act = 0.05)
- Brillo mínimo requerido: V_min = 100 (escala 0-255 en HSV)
- Ventana de confirmación: N ≥ 8 fotogramas

### Impacto
- **Severidad:** Media
- **Causa probable:** LED envejecido, conexión sucia, resistencia de limitación de corriente defectuosa.
- **Acción recomendada:** Alerta al operador, programar mantenimiento preventivo, reemplazo de LED.

---

## 6. OBSTRUCTED_LIGHT (Lente obstruido)

### Descripción
El detector YOLO localiza el cabezal del semáforo, pero una o más lentes no son visibles o están completamente obstruidas (suciedad, vandalismo, objeto bloqueante).

### Condiciones de detección
- El detector YOLO localiza el cabezal (confianza ≥ 0.5).
- El análisis de contraste o bordes en una ROI indica ausencia de estructura visible (lente oscuro sin transiciones cromáticas).
- Alternativamente: la ROI tiene píxeles con valores muy bajos en todos los canales (oscuridad total).
- Esta condición persiste durante ≥ N fotogramas.

### Umbrales
- Confianza mínima del detector: 0.5
- Porcentaje de píxeles oscuros (V < 50 en HSV): > 80% en la ROI
- Ventana de confirmación: N ≥ 8 fotogramas

### Impacto
- **Severidad:** Media
- **Causa probable:** Suciedad acumulada, vandalismo, objeto bloqueante, condensación.
- **Acción recomendada:** Alerta al operador, limpieza o reparación del lente, inspección visual.

---

## Matriz de resumen

| Anomalía | Severidad | Causa probable | Acción |
|---|---|---|---|
| ALL_LIGHTS_OFF | Crítica | Falla de alimentación | Revisión de fuente |
| MULTIPLE_LIGHTS_ON | Crítica | Falla del controlador | Revisión de circuitería |
| INVALID_TRANSITION | Crítica | Corrupción de firmware | Revisión del controlador |
| LIGHT_STUCK | Alta | Contacto pegado | Reinicio o reemplazo |
| LOW_BRIGHTNESS | Media | LED envejecido | Mantenimiento preventivo |
| OBSTRUCTED_LIGHT | Media | Suciedad/vandalismo | Limpieza o reparación |

---

## Notas importantes

1. **Ventana de confirmación (N fotogramas):** Para evitar falsas alarmas por parpadeo transitorio o ruido, toda anomalía debe persistir durante al menos N = 8 fotogramas consecutivos (≈ 0.27 segundos a 30 FPS) antes de ser registrada.

2. **Confianza del detector:** Si la confianza del detector YOLO cae por debajo de 0.5, el sistema entra en estado `UNKNOWN` y no emite alertas hasta recuperar visibilidad.

3. **Histéresis temporal:** Una vez confirmada una anomalía, se mantiene activa hasta que se observe un retorno a operación normal durante al menos N fotogramas.

4. **Evidencia fotográfica:** Cada anomalía confirmada se acompaña de un fotograma de evidencia almacenado en la base de datos SQLite con timestamp exacto.
