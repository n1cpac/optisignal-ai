# Panel de Supervisión - Semáforo (esqueleto preliminar)

Panel en Angular (standalone components + signals) con el diseño de `DESIGN.md` aplicado en CSS puro (sin Tailwind).

## Estructura

```
src/app/
├── core/
│   ├── models/
│   │   ├── status.model.ts   -> SystemStatus (respuesta de /status)
│   │   └── alert.model.ts    -> AlertRecord, AlertFilter (respuesta de /alerts)
│   └── services/
│       └── api.service.ts    -> polling de /status y consulta de /alerts
├── features/
│   ├── dashboard/            -> Panel principal
│   ├── alerts/                -> Módulo de alertas (tabla + filtros + modal evidencia)
│   └── system-status/        -> Información del sistema
├── shared/
│   └── components/
│       ├── traffic-light/    -> Indicador gráfico rojo/amarillo/verde
│       └── alert-card/       -> Tarjeta de una alerta en la tabla histórica
├── app.routes.ts
├── app.config.ts
└── app.component.ts           -> Shell con navegación entre las 3 vistas
```

## Mock del backend (para visualizar sin backend real)

Se agregó un interceptor HTTP en `core/interceptors/mock-api.interceptor.ts`
que responde `/status` (con datos que cambian en cada polling) y `/alerts`
(3 alertas de ejemplo, con filtros funcionando) sin necesidad de levantar
ningún servidor aparte.

Se activa/desactiva con un solo interruptor en `core/mock-api.config.ts`:

```ts
export const USE_MOCK_API = true; // ponlo en false cuando conectes el backend real
```

## Supuestos hechos para este esqueleto

- Backend expone `GET /status` (estado del semáforo, confianza, estado operativo,
  fuente de video, FPS, uso de recursos, contador de alertas) y `GET /alerts`
  (histórico, con filtros `tipoFalla`, `fechaInicio`, `fechaFin` como query params).
- Polling de `/status` cada 1.5s (dentro del rango de 1-2s solicitado), vía
  `ApiService.pollStatus()`.
- No se definió aún la URL base del backend: `ApiService.baseUrl` queda vacío
  (rutas relativas); ajustar cuando exista backend real o configurar un proxy
  de desarrollo (`proxy.conf.json`).
- El modal de evidencia asume que `/alerts` retorna una URL de imagen
  (`fotogramaUrl`) ya accesible; si el backend entrega el fotograma binario,
  habrá que añadir un endpoint/método específico para traerlo.
- Angular 18, standalone components, control flow moderno (`@for`, `@if`).

## Cómo correr

```bash
npm install
npm start
```

Falta manejo de errores/estados de carga; el diseño ya está aplicado (ver siguiente sección).

## Mapa de alertas (Leaflet)

- Ruta `/map` (carga diferida): `features/map/map.component.ts` + `shared/components/alerts-map/`.
- `AlertRecord` ahora incluye `lat` y `lng` (WGS84). El backend real debe enviarlos; las alertas sin coordenadas no se dibujan.
- La malla vial (`src/assets/geo/malla-vial-principal.geojson`, ~3.5 MB) es una versión reducida del GeoJSON completo
  de Bogotá (137.000 tramos, 138 MB): solo tramos con velocidad regulada de 60 km/h, coordenadas a 5 decimales y 2 propiedades.
  Se dibuja como capa de contexto (activable/desactivable) debajo de las alertas.

## Diseño (DESIGN.md → CSS)

- **Tokens y primitivas globales** en `src/styles.css`: colores, tipografías, espaciado, botones (`.btn`), campos (`.campo`),
  tiles (`.tiles`/`.tile`), consola (`.consola`), filas de alertas (`.fila-alerta`) y ajustes de Leaflet.
  Para cambiar la identidad visual basta con editar las variables de `:root`.
- **Estilos propios** dentro de cada componente: cabecera (`app.component.ts`), banda de página (`page-head`),
  semáforo (`traffic-light`), modal (`evidence-modal`).
- **Tipografías:** se cargan los sustitutos de Google Fonts (Cormorant Garamond, DM Sans, IBM Plex Mono) desde `index.html`.
  Si tienes licencia de Season VF / Uncut Sans / Modern Era Mono, decláralas con `@font-face`: las variables
  `--font-*` ya las priorizan sobre los sustitutos.
- **Extensión a DESIGN.md:** rojo/ámbar/verde de señalización (`--signal-*`), solo en las luces del semáforo y marcadores de estado.
- `angular.json` desactiva el inlining de fuentes en producción para que el build no dependa de la red.
- Componente nuevo `evidence-modal`, compartido por Alertas y Mapa (cierra con botón, Esc o clic en el fondo).
