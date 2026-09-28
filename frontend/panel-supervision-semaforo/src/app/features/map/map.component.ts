import { Component, computed, inject, signal } from '@angular/core';

import { ApiService } from '../../core/services/api.service';
import { AlertRecord } from '../../core/models/alert.model';
import { AlertsMapComponent } from '../../shared/components/alerts-map/alerts-map.component';
import { EvidenceModalComponent } from '../../shared/components/evidence-modal/evidence-modal.component';
import { PageHeadComponent } from '../../shared/components/page-head/page-head.component';

@Component({
  selector: 'app-map',
  standalone: true,
  imports: [AlertsMapComponent, EvidenceModalComponent, PageHeadComponent],
  template: `
    <app-page-head
      titulo="Mapa de alertas"
      [descripcion]="descripcion()"
    ></app-page-head>

    <div class="contenedor pagina">
      <div class="marco-mapa">
        <app-alerts-map [alertas]="alertas()" (verEvidencia)="seleccionada.set($event)"></app-alerts-map>
      </div>

      @if (sinUbicacion() > 0) {
        <p class="texto-secundario">
          {{ sinUbicacion() }} {{ sinUbicacion() === 1 ? 'alerta no tiene' : 'alertas no tienen' }}
          coordenadas y no se muestra en el mapa.
        </p>
      }
    </div>

    @if (seleccionada(); as alerta) {
      <app-evidence-modal [alerta]="alerta" (cerrar)="seleccionada.set(null)"></app-evidence-modal>
    }
  `
})
export class MapComponent {
  private api = inject(ApiService);

  alertas = signal<AlertRecord[]>([]);
  seleccionada = signal<AlertRecord | null>(null);

  sinUbicacion = computed(() => this.alertas().filter((a) => a.lat == null || a.lng == null).length);

  descripcion = computed(() => {
    const n = this.alertas().length;
    return n === 1 ? '1 alerta registrada. Pulsa un punto para ver el detalle.'
                   : `${n} alertas registradas. Pulsa un punto para ver el detalle.`;
  });

  constructor() {
    this.api.getAlerts().subscribe((a) => this.alertas.set(a));
  }
}
