# Especificación de la secuencia vial colombiana y clasificación temporal — OptiSignal-AI

## 1. Ciclo vial colombiano implementado

De acuerdo con la normativa nacional de tránsito, todo semáforo vehicular debe seguir la secuencia:

```text
ROJO  ──►  AMARILLO_PREP  ──►  VERDE  ──►  AMARILLO_DESP  ──►  ROJO
```

La máquina de estados finitos (`TrafficLightFSM` en [`backend/app/state_machine.py`](../../backend/app/state_machine.py)) distingue automáticamente si un estado `YELLOW` corresponde a **preparación** (`AMARILLO_PREP`, cuando `last_major_state == "ROJO"`) o a **despeje** (`AMARILLO_DESP`, cuando proviene de `VERDE` o arranque).

---

## 2. Clasificación cromática en cada fotograma (`classifier.py`)

Antes de alimentar la FSM, el estado de cada cabezal se extrae de su bounding box estabilizada siguiendo estos pasos:

1. **Umbral mínimo de lectura:** si la confianza asociada es menor a `0.25` (`confidence_threshold`) o la altura de la ROI es menor a `12 px` (`min_roi_height`), o si `ancho >= alto`, devuelve `UNKNOWN`.
2. **Columna óptica central (75 %):** se recortan los márgenes laterales (`12.5 %` a cada lado cuando `width >= 16`) para evitar que postes amarillos y viseras contaminen la lectura.
3. **Tercios verticales en HSV:** superior (`red`), central (`yellow`) e inferior (`green`), evaluados con los rangos calibrados en [`CONFIG_PARAMETERS.yaml`](../../CONFIG_PARAMETERS.yaml):
   - `red`: `H` `[0..10]` y `[160..179]`, `S >= 36`, `V >= 102`
   - `yellow`: `H` `[8..40]`, `S >= 20`, `V >= 105`
   - `green`: `H` `[45..95]`, `S >= 20`, `V >= 102`
4. **Rescate de *bloom* LED y descuento de cielo:** si el lente tiene corona cromática (`base_ratio >= 0.035`), se incluye el núcleo blanco sobreexpuesto (`S <= 32, V >= 238`); los píxeles de cielo azul o nublado se excluyen del área efectiva del tercio.
5. **Activación y filtro anti-halo:** un lente se activa si su fracción efectiva es `>= 0.08` (`activation_threshold`). Si hay más de un lente activo, `_filter_halo_bleed` descarta lentes secundarios por debajo del `48 %` de la activación dominante.

---

## 3. Reglas temporales, ventana deslizante y sincronización

### Tiempos nominales y máximos (`CONFIG_PARAMETERS.yaml`)

| Fase | $\tau_{\min}$ (referencia) | $\tau_{\max}$ (`TAU_MAX` en FSM) |
| :--- | :---: | :---: |
| `ROJO` | 30 s | 120 s |
| `AMARILLO_PREP` | 3 s | 5 s |
| `VERDE` | 20 s | 90 s |
| `AMARILLO_DESP` | 3 s | 5 s |

### Parámetros de estabilidad temporal

- **Confirmación de cambio (`state_confirmation_seconds = 1.0 s`):** un cambio visual debe sostenerse al menos 1 segundo para aceptarse en la FSM, filtrando parpadeos o errores de un solo fotograma.
- **Resincronización por pérdida de vista (`resync_after_seconds = 2.0 s`):** si un semáforo pasa a `UNKNOWN` más de 2 segundos, la FSM vuelve a `STARTUP` para reenganchar sin falsas alertas de transición.
- **Ventana de amarillo intermitente (`temporal_window_seconds = 5.5 s`):** detecta alternancia `YELLOW` / `OFF` sostenida con `flash_min_Ratio = 0.18` y la reporta como `AMARILLO_INTERMITENTE` en lugar de `ALL_LIGHTS_OFF`.
- **Sincronización de pórtico (`_synchronize_gantry_tracks`):** cuando varios cabezales pertenecen al mismo pórtico y la mayoría confirma un color activo (`RED`, `YELLOW`, `GREEN`), alinea cabezales en ángulo oblicuo que presenten lecturas débiles.
- **Preservación en reinicio de bucle (`on_video_loop`):** al reiniciarse un video de prueba, se conserva el estado confirmado evitando transiciones ficticias al reiniciar la secuencia.

---

## 4. Evaluación agregada de la intersección (`monitor.py`)

Un cruce puede tener varios semáforos numerados `#1..#N` (`Cabezal`). Si algún cabezal confirma anomalía (por ejemplo `ALL_LIGHTS_OFF`, `AMARILLO_INTERMITENTE`, `MULTIPLE_LIGHTS_ON`, `INVALID_TRANSITION`, `LIGHT_STUCK`), el estado operativo de la intersección pasa a `"anomalia"` y el monitor registra la alerta en SQLite bajo deduplicación por escena (`alert_new_scene_threshold: 3.0`, recordatorio `30 min`) protegida por `_alert_lock`.
