import {
  Component, ElementRef, EventEmitter, Input, OnChanges, OnDestroy, OnInit,
  Output, ViewChild, inject
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import * as L from 'leaflet';

import { AlertRecord } from '../../../core/models/alert.model';

const BOGOTA_CENTRO: L.LatLngTuple = [4.65, -74.1];
const URL_MALLA = 'assets/geo/malla-vial-principal.geojson';

@Component({
  selector: 'app-alerts-map',
  standalone: true,
  template: `<div #mapa class="mapa"></div>`,
  styles: [`
    :host { display: block; }
    .mapa { height: 68vh; min-height: 420px; width: 100%; }
  `]
})
export class AlertsMapComponent implements OnInit, OnChanges, OnDestroy {
  @Input() alertas: AlertRecord[] = [];
  @Output() verEvidencia = new EventEmitter<AlertRecord>();

  @ViewChild('mapa', { static: true }) private mapaEl!: ElementRef<HTMLDivElement>;

  private http = inject(HttpClient);
  private map?: L.Map;
  private capaAlertas = L.layerGroup();

  ngOnInit(): void {
    this.map = L.map(this.mapaEl.nativeElement).setView(BOGOTA_CENTRO, 11);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(this.map);

    // Pane propio para que la malla quede SIEMPRE debajo de las alertas
    this.map.createPane('malla').style.zIndex = '350';
    this.capaAlertas.addTo(this.map);

    const controlCapas = L.control.layers(undefined, { 'Alertas': this.capaAlertas }).addTo(this.map);
    this.cargarMalla(controlCapas);
    this.pintarAlertas();
  }

  ngOnChanges(): void {
    // ngOnChanges corre antes de ngOnInit la primera vez: se ignora hasta que el mapa exista
    if (this.map) this.pintarAlertas();
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  private cargarMalla(control: L.Control.Layers): void {
    this.http.get<GeoJSON.FeatureCollection>(URL_MALLA).subscribe((geo) => {
      const malla = L.geoJSON(geo, {
        renderer: L.canvas({ pane: 'malla' }), // canvas: mucho más rápido que SVG con miles de líneas
        interactive: false,
        style: { color: '#384ce3', weight: 1, opacity: 0.45 } // Registry Blue
        // los tipos de Leaflet no declaran 'renderer' en GeoJSONOptions, pero sí lo respeta en ejecución
      } as L.GeoJSONOptions).addTo(this.map!);
      control.addOverlay(malla, 'Malla vial');
    });
  }

  private pintarAlertas(): void {
    this.capaAlertas.clearLayers();
    const puntos: L.LatLngTuple[] = [];

    for (const alerta of this.alertas) {
      if (alerta.lat == null || alerta.lng == null) continue; // sin coordenadas no se puede ubicar

      const punto: L.LatLngTuple = [alerta.lat, alerta.lng];
      puntos.push(punto);

      L.circleMarker(punto, {
        radius: 9, color: '#ffffff', weight: 2, fillColor: '#d92d20', fillOpacity: 1 // rojo de señalización
      })
        .bindPopup(this.crearPopup(alerta))
        .addTo(this.capaAlertas);
    }

    if (puntos.length) {
      this.map!.fitBounds(L.latLngBounds(puntos), { padding: [40, 40], maxZoom: 15 });
    }
  }

  /** Se arma con DOM (textContent) y no con HTML string, para evitar inyección desde datos del backend. */
  private crearPopup(alerta: AlertRecord): HTMLElement {
    // Clases globales (styles.css): el popup lo crea Leaflet fuera del alcance de los estilos del componente
    const cont = document.createElement('div');
    cont.className = 'popup-alerta';

    const titulo = document.createElement('strong');
    titulo.className = 'popup-alerta__titulo';
    titulo.textContent = alerta.tipoFalla;

    const fecha = document.createElement('span');
    fecha.className = 'popup-alerta__fecha';
    fecha.textContent = new Date(alerta.fecha).toLocaleString('es-CO');

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'btn btn--sm';
    boton.textContent = 'Ver evidencia';
    boton.addEventListener('click', () => this.verEvidencia.emit(alerta));

    cont.append(titulo, fecha, boton);
    return cont;
  }
}
