# OptiSignal, panel de supervision de semaforos

Panel unico en Angular (standalone components + signals). Todo se ve en una sola pantalla:

```
+--------------------------------------------------------------+
|  OPTISIGNAL                                                  |
+-------------+-----------------------------+------------------+
| Historial   |                             | Estado semaforo  |
| de reportes |   Mapa de Bogota            | (sistema         |
|             |   (malla vial)              |  electrico)      |
| ubicacion   |                             | Imagen en vivo   |
| fecha       |   [totales]                 | Reporte + envio  |
| descripcion |                             |                  |
+-------------+-----------------------------+------------------+
```

- Clic en un reporte del historial, o en un semaforo del mapa: el mapa se centra, dibuja un
  circulo azul sobre ese semaforo y el panel derecho muestra su detalle.
- Recuadro del mapa: total de semaforos monitoreados, activos sin problemas y con fallas.
- Panel derecho: luz encendida segun el sistema electrico, imagen en vivo, y formulario de reporte
  (coincide / no coincide, texto, y envio a policia de transito y/o tecnicos).

## Estructura

```
src/app/
├── core/
│   ├── models/          semaforo.model.ts, reporte.model.ts
│   ├── services/        api.service.ts (HTTP + polling), panel-state.service.ts (estado compartido)
│   ├── interceptors/    mock-api.interceptor.ts (backend simulado)
│   └── mock-api.config.ts   interruptor USE_MOCK_API
├── features/
│   ├── report-history/  historial de reportes (izquierda)
│   ├── city-map/        mapa MapLibre con la malla vial (centro)
│   └── semaforo-detail/ estado, imagen en vivo y formulario de reporte (derecha)
├── shared/components/
│   ├── traffic-light/   indicador de las tres luces
│   └── report-item/     fila del historial
└── app.component.ts     layout general
src/assets/malla-vial-bogota.geojson   malla vial aligerada
tools/aligerar_geojson.py              script para regenerar el GeoJSON
```

## Como correr

Primero el backend, desde la carpeta `backend/` del repositorio (Python 3.11):

```bash
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8000 --timeout-graceful-shutdown 2
```

Luego el panel, que envia sus peticiones al backend mediante `proxy.conf.json`:

```bash
npm install
npm start
```

Abrir http://localhost:4200. La primera carga del mapa tarda unos segundos porque la malla vial
tiene casi 137.000 tramos (aparece el aviso "Cargando malla vial...").

## Backend

Las camaras y los semaforos se configuran en `semaforos` de `CONFIG_PARAMETERS.yaml`. Para ver el panel
sin backend, `USE_MOCK_API = true` en `src/app/core/mock-api.config.ts` activa un interceptor con datos falsos.

Endpoints que el frontend espera:

| Metodo | Ruta | Respuesta |
|---|---|---|
| GET | `/semaforos` | lista de `Semaforo` (consulta cada 1,5 s) |
| GET | `/reportes?vista=actuales\|historial&pagina=1&tamano=20` | `PaginaReportes` con `items` y `total` (consulta cada 5 s) |
| POST | `/reportes/envio` | recibe `EnvioReporte`, atiende las alertas pendientes del semaforo y responde `{ "ok": true }` |
| POST | `/reportes/{id}/abrir` | marca una alerta como abierta: deja de repetirse como recordatorio |
| GET | `/camaras/{id}/mjpeg` | video anotado con la deteccion de YOLO |

Detalles de `Semaforo` (ver `core/models/semaforo.model.ts`):

- `estadoElectrico`: `rojo`, `amarillo`, `verde`, `apagado` o `multiple`, segun el sistema electrico del
  semaforo. `lucesElectricas` dice cuales estan encendidas.
- `estadoVisual`: lo que ve la camara con YOLO + HSV. Ademas de las luces puede ser `multiple`,
  `sin_deteccion`, `desconocido` o `sin_senal`. `lucesDetectadas` y `confianza` lo detallan.
- `estadoOperativo`: `normal` o `anomalia` (define el color del punto en el mapa y los totales).
- `fuenteImagen`: `obs` muestra la camara virtual de OBS en el navegador; `url` (por defecto) muestra `imagenUrl`.
- `imagenUrl`: imagen en vivo cuando la fuente es `url`. Puede ser una transmision MJPEG (el navegador la
  muestra sola dentro de un `<img>`) o una captura cuya URL cambia cuando hay una imagen nueva. El
  frontend usa la URL tal cual, sin agregarle parametros.

## Camara en vivo con OBS

El componente `shared/components/live-camera` abre la camara con `getUserMedia` y elige el dispositivo
cuyo nombre contiene "OBS" (la camara virtual de OBS). Si no la encuentra, usa la camara predeterminada.
En el mock, el semaforo `s2` (AC 72 con KR 13) usa esta fuente y los demas muestran capturas de
`src/assets/semaforos/` (rojo, amarillo, apagado y rojo con verde); se cambia con `obs: true` en
`mock-api.interceptor.ts`, o con `fuenteImagen: 'obs'` en la respuesta del backend real.

Para probar:

1. En OBS, arma la escena con la fuente de video del semaforo (camara, captura de ventana, etc.).
2. En el panel "Controles" de OBS, pulsa "Iniciar camara virtual".
3. En el panel, selecciona el semaforo `AC 72 con KR 13` y permite el acceso a la camara cuando el
   navegador lo pida.

Notas:

- `getUserMedia` solo funciona en `localhost` o con HTTPS.
- Si inicias la camara virtual de OBS despues de abrir el panel, el componente cambia a ella solo, o
  usa el boton "Reintentar".
- La camara se libera al seleccionar otro semaforo, para no dejarla abierta sin necesidad.

## Malla vial

El GeoJSON original (Malla Vial Integral de Bogota, unos 138 MB) es demasiado pesado para el
navegador. `tools/aligerar_geojson.py` conserva solo el tipo de via, la etiqueta y la velocidad
reglamentada, y redondea las coordenadas a 5 decimales. El resultado pesa unos 24 MB
(unos 3 MB comprimido). Para regenerarlo:

```bash
python tools/aligerar_geojson.py ruta/al/original.geojson src/assets/malla-vial-bogota.geojson
```

Las coordenadas de los semaforos del mock son intersecciones reales de esa malla, usadas solo como
ubicaciones de ejemplo.

## Pendiente

- Diseno visual (colores, tipografia, iconos); ahora solo hay un layout funcional.
- Mapa base con edificios, parques y rios como en la maqueta (hoy solo se dibuja la malla vial).
- Filtros del historial (por tipo de falla y fecha), que existian en el esqueleto anterior.
