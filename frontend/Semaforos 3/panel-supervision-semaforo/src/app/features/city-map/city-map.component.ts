import {
  AfterViewInit,
  Component,
  ElementRef,
  HostBinding,
  NgZone,
  OnDestroy,
  ViewChild,
  computed,
  effect,
  inject,
  signal,
  untracked
} from '@angular/core';
import {
  AttributionControl,
  FilterSpecification,
  GeoJSONSource,
  Map as MaplibreMap,
  MapLayerMouseEvent,
  Popup
} from 'maplibre-gl';
import type { FeatureCollection, Point } from 'geojson';

import { PanelStateService } from '../../core/services/panel-state.service';
import { Semaforo } from '../../core/models/semaforo.model';

const LIMITES_BOGOTA: [[number, number], [number, number]] = [[-74.25, 4.45], [-74.0, 4.84]];
const CLAVE_MODO = 'optisignal.modoMapa';

type Filtro = 'todos' | 'fallas' | 'ok';
type ModoMapa = 'oscuro' | 'claro';

const ES_FALLA: FilterSpecification = ['==', ['get', 'estadoOperativo'], 'anomalia'];
const NINGUNO: FilterSpecification = ['==', ['get', 'estadoOperativo'], ''];

function modoGuardado(): ModoMapa {
  try {
    return localStorage.getItem(CLAVE_MODO) === 'claro' ? 'claro' : 'oscuro';
  } catch {
    return 'oscuro'; // almacenamiento bloqueado o no disponible
  }
}

/** MapLibre no entiende variables CSS: se leen del :root para que los colores sigan viviendo en styles.css. */
function paleta(modo: ModoMapa) {
  const estilos = getComputedStyle(document.documentElement);
  const token = (nombre: string) => estilos.getPropertyValue(`--mapa-${modo}-${nombre}`).trim();
  return {
    fondo: token('fondo'),
    via: token('via'),
    borde: token('borde'),
    falla: token('falla'),
    ok: token('ok'),
    seleccion: token('seleccion')
  };
}

@Component({
  selector: 'app-city-map',
  standalone: true,
  template: `
    <div #contenedor class="mapa"></div>

    @if (cargandoMalla()) {
      <div class="cargando" role="status">Cargando malla vial...</div>
    }

    <div class="filtro" role="group" aria-label="Filtrar semáforos">
      @for (op of opciones(); track op.valor) {
        <button type="button" [class.activo]="filtro() === op.valor" [attr.aria-pressed]="filtro() === op.valor" (click)="filtro.set(op.valor)">
          <i class="punto" [class]="op.valor"></i>
          {{ op.texto }}
          <span class="conteo">({{ op.cantidad }})</span>
        </button>
      }
    </div>

    <div class="controles">
      <button
        type="button"
        class="control"
        [attr.aria-label]="modo() === 'claro' ? 'Cambiar a mapa oscuro' : 'Cambiar a mapa claro'"
        (click)="alternarModo()"
      >
        <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
          <path class="horizonte" d="M3 18h18" />
          <path class="sol" [class.claro]="modo() === 'claro'" d="M7 18a5 5 0 0 1 10 0z" />
          @if (modo() === 'claro') {
            <g class="rayos">
              <path d="M19.2 15.1l2.5-.7M16.6 11.1l1.6-2M12 9.5V7M7.4 11.1l-1.6-2M4.8 15.1l-2.5-.7" />
            </g>
          }
        </svg>
      </button>
      <div class="zoom">
        <button type="button" class="control" aria-label="Acercar" (click)="mapa?.zoomIn()">+</button>
        <button type="button" class="control" aria-label="Alejar" (click)="mapa?.zoomOut()">−</button>
      </div>
    </div>
  `,
  styles: [`
    :host {
      --mapa-fondo: var(--mapa-oscuro-fondo);
      display: block;
      position: relative;
      width: 100%;
      height: 100%;
      background: var(--mapa-fondo);
    }
    :host(.mapa-claro) { --mapa-fondo: var(--mapa-claro-fondo); }
    .mapa { position: absolute; inset: 0; background: var(--mapa-fondo); }
    .cargando {
      position: absolute;
      z-index: 1;
      left: 12px;
      bottom: 28px;
      padding: 8px 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-control);
      color: var(--text-muted);
      font-size: 13px;
    }

    .filtro, .controles { position: absolute; z-index: 1; top: 12px; }
    .filtro {
      left: 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      max-width: calc(100% - 132px);
      padding: 4px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-panel);
    }
    .filtro button {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 36px;
      padding: 0 12px;
      border: 1px solid transparent;
      border-radius: var(--r-control);
      background: transparent;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
    }
    .filtro button:hover { background: color-mix(in srgb, var(--border) 50%, transparent); }
    .filtro button.activo {
      color: var(--accent);
      border-color: var(--accent);
      background: color-mix(in srgb, var(--accent) 14%, transparent);
    }
    .punto { width: 8px; height: 8px; border-radius: 50%; }
    .punto.todos { background: var(--accent); }
    .punto.fallas { background: var(--danger); }
    .punto.ok { background: var(--ok); }
    .conteo { font-family: var(--font-mono); font-size: 12px; }

    .controles { right: 12px; display: flex; align-items: flex-start; gap: 8px; }
    .zoom { display: flex; flex-direction: column; gap: 4px; }
    .control {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border: 1px solid var(--border);
      border-radius: var(--r-control);
      background: var(--surface);
      color: var(--text);
      font-size: 22px;
      line-height: 1;
      cursor: pointer;
    }
    .control:hover { border-color: var(--accent); }
    .horizonte, .sol, .rayos path { fill: none; stroke: var(--text-muted); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
    .sol.claro, .rayos path { stroke: var(--warning); }
    .sol.claro { fill: var(--warning); }

    @media (max-width: 520px) {
      .filtro button { padding: 0 8px; }
    }
  `]
})
export class CityMapComponent implements AfterViewInit, OnDestroy {
  protected state = inject(PanelStateService);
  private zone = inject(NgZone);

  @ViewChild('contenedor', { static: true }) contenedor!: ElementRef<HTMLDivElement>;

  protected cargandoMalla = signal(true);
  protected filtro = signal<Filtro>('todos');
  protected modo = signal<ModoMapa>(modoGuardado());
  protected opciones = computed(() => {
    const r = this.state.resumen();
    return [
      { valor: 'todos' as Filtro, texto: 'Todos', cantidad: r.total },
      { valor: 'fallas' as Filtro, texto: 'Con fallas', cantidad: r.conFallas },
      { valor: 'ok' as Filtro, texto: 'Sin problemas', cantidad: r.activos }
    ];
  });

  @HostBinding('class.mapa-claro') protected get esClaro(): boolean {
    return this.modo() === 'claro';
  }

  private mapaListo = signal(false);
  protected mapa?: MaplibreMap;
  private etiqueta?: Popup;
  private redimension?: ResizeObserver;
  private ultimaFirmaSemaforos = '';
  /** Cambia solo cuando cambia el semaforo seleccionado o su estado: evita rehacer la etiqueta en cada consulta. */
  private claveEtiqueta = computed(() => {
    const s = this.state.seleccionado();
    return s ? `${s.id}|${s.nombre}|${s.estadoOperativo}|${s.lng}|${s.lat}` : '';
  });

  constructor() {
    // Actualiza los puntos de los semaforos solo cuando cambian sus coordenadas o estado operativo
    effect(() => {
      const lista = this.state.semaforos();
      if (!this.mapaListo() || !this.mapa) return;
      const firma = lista.map((s) => `${s.id}:${s.lng}:${s.lat}:${s.estadoOperativo}`).join('|');
      if (firma === this.ultimaFirmaSemaforos) return;
      this.ultimaFirmaSemaforos = firma;
      this.zone.runOutsideAngular(() => {
        (this.mapa!.getSource('semaforos') as GeoJSONSource).setData(this.aGeoJson(lista));
      });
    });

    // Dibuja el anillo de seleccion y centra el mapa cuando cambia el semaforo seleccionado.
    // Solo depende del id: las coordenadas no cambian con cada consulta.
    effect(() => {
      const id = this.state.seleccionadoId();
      if (!this.mapaListo() || !this.mapa) return;
      const sel = untracked(() => this.state.semaforos().find((s) => s.id === id));
      this.zone.runOutsideAngular(() => {
        (this.mapa!.getSource('seleccion') as GeoJSONSource).setData(
          this.aGeoJson(sel ? [sel] : [])
        );
        if (sel) {
          this.mapa!.flyTo({
            center: [sel.lng, sel.lat],
            zoom: Math.max(this.mapa!.getZoom(), 14),
            essential: true
          });
        }
      });
    });

    // Etiqueta flotante sobre el seleccionado: direccion y estado
    effect(() => {
      this.claveEtiqueta();
      if (!this.mapaListo() || !this.mapa) return;
      const sel = untracked(() => this.state.seleccionado());
      this.zone.runOutsideAngular(() => this.mostrarEtiqueta(sel));
    });

    // El filtro solo oculta o muestra marcadores; no toca la lista de incidencias ni el panel de detalle
    effect(() => {
      const filtro = this.filtro();
      if (!this.mapaListo() || !this.mapa) return;
      const filtroMarcadores: FilterSpecification | null =
        filtro === 'fallas' ? ES_FALLA : filtro === 'ok' ? ['!=', ['get', 'estadoOperativo'], 'anomalia'] : null;
      this.zone.runOutsideAngular(() => {
        this.mapa!.setFilter('semaforos', filtroMarcadores);
        this.mapa!.setFilter('semaforos-halo', filtro === 'ok' ? NINGUNO : ES_FALLA);
      });
    });

    // Modo claro u oscuro: solo estilo de la capa GeoJSON, fondo y marcadores
    effect(() => {
      const modo = this.modo();
      if (!this.mapaListo() || !this.mapa) return;
      this.zone.runOutsideAngular(() => this.aplicarModo(this.mapa!, modo));
    });
  }

  ngAfterViewInit(): void {
    // El mapa se crea fuera de la zona de Angular para no disparar deteccion de cambios en cada movimiento
    this.zone.runOutsideAngular(() => {
      const mapa = new MaplibreMap({
        container: this.contenedor.nativeElement,
        style: {
          version: 8,
          sources: {},
          layers: [{ id: 'fondo', type: 'background', paint: { 'background-color': paleta(this.modo()).fondo } }]
        },
        bounds: LIMITES_BOGOTA,
        fitBoundsOptions: { padding: 20 },
        attributionControl: false
      });

      mapa.addControl(
        new AttributionControl({ compact: false, customAttribution: 'Malla Vial Integral de Bogotá D.C.' }),
        'bottom-right'
      );

      mapa.on('load', () => this.configurarCapas(mapa));
      mapa.on('sourcedata', (e) => {
        if (e.sourceId === 'malla' && e.isSourceLoaded) {
          this.zone.run(() => this.cargandoMalla.set(false));
        }
      });

      // MapLibre solo escucha cambios de la ventana; al expandir la camara cambia el contenedor
      this.redimension = new ResizeObserver(() => mapa.resize());
      this.redimension.observe(this.contenedor.nativeElement);

      this.mapa = mapa;
    });
  }

  ngOnDestroy(): void {
    this.redimension?.disconnect();
    this.etiqueta?.remove();
    this.mapa?.remove();
  }

  protected alternarModo(): void {
    const nuevo: ModoMapa = this.modo() === 'claro' ? 'oscuro' : 'claro';
    this.modo.set(nuevo);
    try {
      localStorage.setItem(CLAVE_MODO, nuevo);
    } catch {
      // sin almacenamiento: el modo vale solo para esta sesion
    }
  }

  private configurarCapas(mapa: MaplibreMap): void {
    const c = paleta(this.modo());

    // 1. Malla vial en un solo color: el GeoJSON solo trae 'etiqueta' (ej. "AC 1"), sin tipo de via,
    //    y resaltar avenidas por su nombre dejaba cortes en cruces, puentes y glorietas
    mapa.addSource('malla', {
      type: 'geojson',
      data: new URL('assets/malla-vial-bogota.geojson', document.baseURI).href,
      tolerance: 0.6,
      buffer: 64,
      maxzoom: 16
    });
    mapa.addLayer({
      id: 'malla-vial',
      type: 'line',
      source: 'malla',
      paint: { 'line-color': c.via, 'line-width': 1, 'line-opacity': 0.9 }
    });

    // 2. Semaforos: sin problemas (12px) o con falla (16px y halo de 6px al 25 %)
    mapa.addSource('semaforos', { type: 'geojson', data: this.aGeoJson(this.state.semaforos()) });
    mapa.addLayer({
      id: 'semaforos-halo',
      type: 'circle',
      source: 'semaforos',
      filter: ES_FALLA,
      paint: { 'circle-radius': 14, 'circle-color': c.falla, 'circle-opacity': 0.25 }
    });

    // 3. Anillo de seleccion de 56px bajo el punto, para que el punto quede al centro
    mapa.addSource('seleccion', { type: 'geojson', data: this.aGeoJson([]) });
    mapa.addLayer({
      id: 'seleccion',
      type: 'circle',
      source: 'seleccion',
      paint: {
        'circle-radius': 28,
        'circle-color': c.seleccion,
        'circle-opacity': 0.12,
        'circle-stroke-color': c.seleccion,
        'circle-stroke-width': 2,
        'circle-stroke-opacity': 1
      }
    });
    mapa.addLayer({
      id: 'semaforos',
      type: 'circle',
      source: 'semaforos',
      paint: {
        'circle-radius': ['match', ['get', 'estadoOperativo'], 'anomalia', 8, 6],
        'circle-color': ['match', ['get', 'estadoOperativo'], 'anomalia', c.falla, c.ok],
        'circle-stroke-color': c.borde,
        'circle-stroke-width': 2
      }
    });

    // Clic en un semaforo del mapa
    mapa.on('click', 'semaforos', (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.['id'];
      if (id) this.zone.run(() => this.state.seleccionar(String(id)));
    });
    mapa.on('mouseenter', 'semaforos', () => (mapa.getCanvas().style.cursor = 'pointer'));
    mapa.on('mouseleave', 'semaforos', () => (mapa.getCanvas().style.cursor = ''));

    this.zone.run(() => this.mapaListo.set(true));
  }

  private aplicarModo(mapa: MaplibreMap, modo: ModoMapa): void {
    const c = paleta(modo);
    mapa.setPaintProperty('fondo', 'background-color', c.fondo);
    mapa.setPaintProperty('malla-vial', 'line-color', c.via);
    mapa.setPaintProperty('malla-vial', 'line-opacity', modo === 'oscuro' ? 0.9 : 1);
    mapa.setPaintProperty('semaforos-halo', 'circle-color', c.falla);
    mapa.setPaintProperty('seleccion', 'circle-color', c.seleccion);
    mapa.setPaintProperty('seleccion', 'circle-stroke-color', c.seleccion);
    mapa.setPaintProperty('semaforos', 'circle-color', ['match', ['get', 'estadoOperativo'], 'anomalia', c.falla, c.ok]);
    mapa.setPaintProperty('semaforos', 'circle-stroke-color', c.borde);
  }

  private mostrarEtiqueta(sel: Semaforo | null | undefined): void {
    this.etiqueta?.remove();
    this.etiqueta = undefined;
    if (!sel || !this.mapa) return;
    const falla = sel.estadoOperativo === 'anomalia';
    const contenido = document.createElement('div');
    const direccion = document.createElement('strong');
    direccion.textContent = sel.nombre;
    const estado = document.createElement('span');
    estado.className = falla ? 'falla' : 'ok';
    estado.textContent = falla ? 'Anomalía eléctrica' : 'Sin problemas';
    contenido.append(direccion, estado);
    this.etiqueta = new Popup({ closeButton: false, closeOnClick: false, anchor: 'bottom', offset: 36, className: 'etiqueta-semaforo' })
      .setLngLat([sel.lng, sel.lat])
      .setDOMContent(contenido)
      .addTo(this.mapa);
  }

  private aGeoJson(lista: Semaforo[]): FeatureCollection<Point> {
    return {
      type: 'FeatureCollection',
      features: lista.map((s) => ({
        type: 'Feature',
        properties: { id: s.id, nombre: s.nombre, estadoOperativo: s.estadoOperativo },
        geometry: { type: 'Point', coordinates: [s.lng, s.lat] }
      }))
    };
  }
}
