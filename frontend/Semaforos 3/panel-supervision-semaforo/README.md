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
│   └── services/        api.service.ts (HTTP + polling), panel-state.service.ts (estado compartido)
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

Las camaras y los semaforos se configuran en `semaforos` de `CONFIG_PARAMETERS.yaml`. El panel necesita
el backend corriendo: sin el, el mapa carga pero no muestra semaforos ni reportes.

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
- `imagenUrl`: video en vivo de la camara, como transmision MJPEG anotada por el backend (el navegador
  la muestra sola dentro de un `<img>`). El frontend usa la URL tal cual, sin agregarle parametros.

La camara virtual de OBS la lee el backend (con `source: 0` en `CONFIG_PARAMETERS.yaml`), no el navegador.

## Malla vial

El GeoJSON original (Malla Vial Integral de Bogota, unos 138 MB) es demasiado pesado para el
navegador. `tools/aligerar_geojson.py` conserva solo el tipo de via, la etiqueta (nombre de la via,
ej. `KR 13`) y la velocidad reglamentada, y redondea las coordenadas a 5 decimales. El resultado pesa
unos 24 MB (unos 3 MB comprimido).

El mapa no usa los atributos, pero el backend si: con las etiquetas ubica cada semaforo en el cruce
que dice su nombre (`AC 72 con KR 13`), asi que no hay que quitarlas. Para regenerarlo:

```bash
python tools/aligerar_geojson.py ruta/al/original.geojson src/assets/malla-vial-bogota.geojson
```

## Pendiente

- Diseno visual (colores, tipografia, iconos); ahora solo hay un layout funcional.
- Mapa base con edificios, parques y rios como en la maqueta (hoy solo se dibuja la malla vial).
- Filtros del historial (por tipo de falla y fecha), que existian en el esqueleto anterior.
