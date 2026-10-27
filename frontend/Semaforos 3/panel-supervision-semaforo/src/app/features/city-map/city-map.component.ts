import {
  AfterViewInit,
  Component,
  ElementRef,
  NgZone,
  OnDestroy,
  ViewChild,
  effect,
  inject,
  signal,
  untracked
} from '@angular/core';
import {
  AttributionControl,
  GeoJSONSource,
  Map as MaplibreMap,
  MapLayerMouseEvent,
  NavigationControl
} from 'maplibre-gl';
import type { FeatureCollection, Point } from 'geojson';

import { PanelStateService } from '../../core/services/panel-state.service';
import { Semaforo } from '../../core/models/semaforo.model';

const LIMITES_BOGOTA: [[number, number], [number, number]] = [[-74.25, 4.45], [-74.0, 4.84]];
const COLOR_NORMAL = '#76c410';
const COLOR_FALLA = '#e53935';
const COLOR_SELECCION = '#1e6fff';

@Component({
  selector: 'app-city-map',
  standalone: true,
  template: `
    <div #contenedor class="mapa"></div>

    @if (cargandoMalla()) {
      <div class="cargando">Cargando malla vial...</div>
    }

    <div class="resumen">
      <strong>Semáforos monitoreados: {{ state.resumen().total }}</strong>
      <span><i class="punto normal"></i>Activos sin problemas: {{ state.resumen().activos }}</span>
      <span><i class="punto falla"></i>Con fallas: {{ state.resumen().conFallas }}</span>
    </div>
  `,
  styles: [`
    :host { display: block; position: relative; width: 100%; height: 100%; }
    .mapa { position: absolute; inset: 0; }
    .resumen, .cargando {
      position: absolute;
      z-index: 1;
      background: #fff;
      border: 2px solid #222;
      padding: 8px 12px;
      font-size: 14px;
    }
    .resumen { left: 12px; bottom: 28px; display: flex; flex-direction: column; gap: 3px; }
    .cargando { left: 12px; top: 12px; }
    .punto { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
    .punto.normal { background: ${COLOR_NORMAL}; }
    .punto.falla { background: ${COLOR_FALLA}; }
  `]
})
export class CityMapComponent implements AfterViewInit, OnDestroy {
  protected state = inject(PanelStateService);
  private zone = inject(NgZone);

  @ViewChild('contenedor', { static: true }) contenedor!: ElementRef<HTMLDivElement>;

  protected cargandoMalla = signal(true);
  private mapaListo = signal(false);
  private mapa?: MaplibreMap;

  constructor() {
    // Actualiza los puntos de los semaforos en cada consulta
    effect(() => {
      const lista = this.state.semaforos();
      if (!this.mapaListo() || !this.mapa) return;
      this.zone.runOutsideAngular(() => {
        (this.mapa!.getSource('semaforos') as GeoJSONSource).setData(this.aGeoJson(lista));
      });
    });

    // Dibuja el circulo azul y centra el mapa cuando cambia el semaforo seleccionado.
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
  }

  ngAfterViewInit(): void {
    // El mapa se crea fuera de la zona de Angular para no disparar deteccion de cambios en cada movimiento
    this.zone.runOutsideAngular(() => {
      const mapa = new MaplibreMap({
        container: this.contenedor.nativeElement,
        style: {
          version: 8,
          sources: {},
          layers: [{ id: 'fondo', type: 'background', paint: { 'background-color': '#ffffff' } }]
        },
        bounds: LIMITES_BOGOTA,
        fitBoundsOptions: { padding: 20 },
        attributionControl: false
      });

      mapa.addControl(new NavigationControl({ showCompass: false }), 'top-right');
      mapa.addControl(
        new AttributionControl({ customAttribution: 'Malla Vial Integral de Bogotá D.C.' }),
        'bottom-right'
      );

      mapa.on('load', () => this.configurarCapas(mapa));
      mapa.on('sourcedata', (e) => {
        if (e.sourceId === 'malla' && e.isSourceLoaded) {
          this.zone.run(() => this.cargandoMalla.set(false));
        }
      });

      this.mapa = mapa;
    });
  }

  ngOnDestroy(): void {
    this.mapa?.remove();
  }

  private configurarCapas(mapa: MaplibreMap): void {
    // 1. Malla vial: todas las vias en gris claro y las avenidas (AC, AK) mas oscuras y gruesas
    mapa.addSource('malla', {
      type: 'geojson',
      data: new URL('assets/malla-vial-bogota.geojson', document.baseURI).href
    });
    mapa.addLayer({
      id: 'malla-vial',
      type: 'line',
      source: 'malla',
      paint: {
        'line-color': '#b0b0b0',
        'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.3, 14, 0.8, 18, 3]
      }
    });
    mapa.addLayer({
      id: 'malla-avenidas',
      type: 'line',
      source: 'malla',
      filter: ['in', ['get', 'tipo'], ['literal', ['AC', 'AK']]],
      paint: {
        'line-color': '#444444',
        'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.8, 14, 2, 18, 6]
      }
    });

    // 2. Semaforos: verde si esta normal, rojo si presenta falla
    mapa.addSource('semaforos', { type: 'geojson', data: this.aGeoJson(this.state.semaforos()) });
    mapa.addLayer({
      id: 'semaforos',
      type: 'circle',
      source: 'semaforos',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 5, 14, 9],
        'circle-color': ['match', ['get', 'estadoOperativo'], 'anomalia', COLOR_FALLA, COLOR_NORMAL],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.5
      }
    });

    // 3. Circulo azul sobre el semaforo seleccionado
    mapa.addSource('seleccion', { type: 'geojson', data: this.aGeoJson([]) });
    mapa.addLayer({
      id: 'seleccion',
      type: 'circle',
      source: 'seleccion',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 12, 14, 18],
        'circle-opacity': 0,
        'circle-stroke-color': COLOR_SELECCION,
        'circle-stroke-width': 3
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
