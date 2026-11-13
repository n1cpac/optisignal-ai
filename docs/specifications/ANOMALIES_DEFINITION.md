# Definición formal de anomalías — OptiSignal-AI

## Introducción

Este documento describe las anomalías y condiciones operativas auditadas por el sistema actual sobre la intersección y por cada cabezal individual (`#1..#N`), reflejando la lógica implementada en [`classifier.py`](../../backend/app/classifier.py), [`tracker.py`](../../backend/app/tracker.py), [`state_machine.py`](../../backend/app/state_machine.py) y [`CONFIG_PARAMETERS.yaml`](../../CONFIG_PARAMETERS.yaml).

---

## 1. `ALL_LIGHTS_OFF` (Apagado total)

- **Descripción:** Ninguno de los tres lentes (rojo, amarillo, verde) supera el umbral de activación de forma sostenida.
- **Condiciones reales en el pipeline:**
  - En el clasificador HSV (`classifier.py`), los tres tercios verticales de la columna central (75 % del ancho de la ROI) obtienen una fracción de píxeles encendidos menor a `activation_threshold: 0.08`.
  - El tracker verifica que **no exista patrón de parpadeo amarillo** en la ventana temporal (`5.5 s`) y que la ausencia de luz persista superando la histéresis del sistema.
  - **Protección contra falsos apagados:** si un semáforo ya demostró estar encendido en el ciclo (`ever_lit`) y no parpadea en amarillo, o tiene baja confianza transitoria al reiniciar bucle (`peak_confidence < 0.75`), **no** se degrada falsamente a `ALL_LIGHTS_OFF`.
- **Severidad:** Crítica.

---

## 2. `AMARILLO_INTERMITENTE` (Parpadeo preventivo / intermitente)

- **Descripción:** Condición incorporada tras las pruebas con cámaras reales de Bogotá (`s1` AK 80 con AC 55 S, `s5` KR 14 con CL 44 S), donde uno o más semáforos alternan indefinidamente entre **amarillo encendido y apagado**.
- **Por qué fue necesaria:** Sin análisis temporal, los fotogramas apagados entre destellos disparaban falsas alertas de `ALL_LIGHTS_OFF` o alternaban erráticamente entre `AMARILLO`, `APAGADO` y `MULTIPLE`.
- **Condiciones reales en el pipeline (`tracker.py`):**
  - Se analiza la secuencia temporal dentro de `temporal_window_seconds: 5.5` segundos.
  - Se verifica alternancia efectiva entre lecturas `YELLOW` y `OFF` con una proporción mínima de amarillo (`flash_min_Ratio: 0.18`).
  - El cabezal pasa a estado visual `amarillo_intermitente` y la FSM (`CONDITION_ANOMALIES["FLASHING_YELLOW"]`) consolida la alerta `AMARILLO_INTERMITENTE` sin confundirla con `ALL_LIGHTS_OFF`.
- **Severidad:** Operativa / Alerta de precaución.

---

## 3. `MULTIPLE_LIGHTS_ON` (Múltiples luces encendidas)

- **Descripción:** Dos o más lentes emiten luz al mismo tiempo en la misma ROI.
- **Condiciones reales en el pipeline (`classifier.py` + `tracker.py`):**
  - El detector marca dos o más tercios con fracción de píxeles `>= 0.08`.
  - **Filtro anti-sangrado (`_filter_halo_bleed`):** para evitar falsos positivos por deslumbramiento (*bloom*) nocturno de un LED muy brillante hacia el lente vecino, una segunda luz solo cuenta como activa si alcanza al menos el **`48 %`** de la activación del lente dominante.
  - La condición debe confirmarse temporalmente (`state_confirmation_seconds: 1.0 s`).
- **Severidad:** Crítica.

---

## 4. `INVALID_TRANSITION` (Transición no reglamentaria)

- **Descripción:** Salto en la secuencia vial colombiana (por ejemplo, `ROJO -> VERDE` o `VERDE -> ROJO` sin paso obligatorio por amarillo).
- **Condiciones reales en el pipeline (`state_machine.py`):**
  - Un nuevo estado visual solo se acepta tras mantenerse continuo al menos `state_confirmation_seconds: 1.0 s`.
  - Si el cambio entre estados mayores válidos (`NEXT_STATE`) viola el ciclo colombiano, se emite `INVALID_TRANSITION` hasta el siguiente cambio válido.
  - Si el semáforo se pierde de vista más de `resync_after_seconds: 2.0 s`, la FSM resincroniza en `STARTUP` para no inventar saltos ilegales por oclusión.
- **Severidad:** Crítica.

---

## 5. `LIGHT_STUCK` (Luz atascada / permanencia excesiva)

- **Descripción:** Un color permanece encendido superando su tiempo máximo nominal $\tau_{\max}$.
- **Tiempos $\tau_{\max}$ configurados (`CONFIG_PARAMETERS.yaml`):**
  - `ROJO`: `120 s`
  - `AMARILLO_PREP`: `5 s`
  - `VERDE`: `90 s`
  - `AMARILLO_DESP`: `5 s`
- **Protección de tiempo:** el tiempo fuera de vista (`UNKNOWN`) o los reinicios de bucle de video no acumulan tiempo falso hacia `LIGHT_STUCK`, y si el cabezal está activo bajo sincronización normal se suprimen falsos `LIGHT_STUCK` transitorios.
- **Severidad:** Alta.

---

## 6. Condiciones adicionales configuradas (`LOW_BRIGHTNESS` y `OBSTRUCTED_LIGHT`)

- `CONFIG_PARAMETERS.yaml` mantiene umbrales de referencia para `low_brightness` (`brightness_threshold: 100`) y `obstructed_light` (`dark_pixel_threshold: 0.8`), quedando el análisis activo centrado en los estados cromáticos HSV y las cinco condiciones temporales/ópticas anteriores validadas en producción.

---

## Matriz resumen de operación actual

| Código | Significado | Filtro anti-ruido aplicado |
| :--- | :--- | :--- |
| `ALL_LIGHTS_OFF` | Apagón total sostenido | Histéresis + exclusión si `is_flashing_yellow` o `ever_lit` con caída breve |
| `AMARILLO_INTERMITENTE` | Parpadeo amarillo continuo | Ventana temporal `5.5 s` con alternancia `YELLOW`/`OFF` y `flash_min_Ratio: 0.18` |
| `MULTIPLE_LIGHTS_ON` | Varias luces activas a la vez | Columna central 75 % + filtro `_filter_halo_bleed` (`>= 48 %` del dominante) |
| `INVALID_TRANSITION` | Salto de secuencia vial | Confirmación `1.0 s` + resincronización tras `2.0 s` sin señal |
| `LIGHT_STUCK` | Permanencia mayor a $\tau_{\max}$ | Reloj detenido durante pérdida de vista y reseteado en reinicios de bucle |
