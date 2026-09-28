import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { AlertRecord, AlertFilter } from '../../core/models/alert.model';
import { AlertCardComponent } from '../../shared/components/alert-card/alert-card.component';
import { EvidenceModalComponent } from '../../shared/components/evidence-modal/evidence-modal.component';
import { PageHeadComponent } from '../../shared/components/page-head/page-head.component';

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [FormsModule, AlertCardComponent, EvidenceModalComponent, PageHeadComponent],
  template: `
    <app-page-head
      titulo="Módulo de alertas"
      descripcion="Historial de fallas detectadas. Filtra por tipo o rango de fechas y revisa el fotograma de cada una."
    ></app-page-head>

    <div class="contenedor pagina">
      <form class="barra-filtros" (ngSubmit)="buscar()">
        <label class="campo">
          <span class="etiqueta">Tipo de falla</span>
          <input type="text" name="tipoFalla" [(ngModel)]="filtro.tipoFalla" />
        </label>
        <label class="campo">
          <span class="etiqueta">Desde</span>
          <input type="date" name="fechaInicio" [(ngModel)]="filtro.fechaInicio" />
        </label>
        <label class="campo">
          <span class="etiqueta">Hasta</span>
          <input type="date" name="fechaFin" [(ngModel)]="filtro.fechaFin" />
        </label>
        <div class="barra-filtros__acciones">
          <button type="submit" class="btn btn--primario">Filtrar</button>
          <button type="button" class="btn" (click)="limpiar()">Limpiar</button>
        </div>
      </form>

      <div class="tabla-alertas">
        <div class="fila-alerta fila-alerta--encabezado etiqueta">
          <span>Falla</span>
          <span>Fecha</span>
          <span>Evidencia</span>
        </div>

        @for (alerta of alertas(); track alerta.id) {
          <app-alert-card [alerta]="alerta" (verEvidencia)="abrirModal($event)"></app-alert-card>
        } @empty {
          <div class="vacio">
            <p>No hay alertas con estos filtros</p>
            <p>Amplía el rango de fechas o borra el tipo de falla.</p>
          </div>
        }
      </div>
    </div>

    @if (alertaSeleccionada(); as alerta) {
      <app-evidence-modal [alerta]="alerta" (cerrar)="cerrarModal()"></app-evidence-modal>
    }
  `
})
export class AlertsComponent {
  private api = inject(ApiService);

  alertas = signal<AlertRecord[]>([]);
  alertaSeleccionada = signal<AlertRecord | null>(null);
  filtro: AlertFilter = {};

  constructor() {
    this.buscar();
  }

  buscar(): void {
    this.api.getAlerts(this.filtro).subscribe((a) => this.alertas.set(a));
  }

  limpiar(): void {
    this.filtro = {};
    this.buscar();
  }

  abrirModal(alerta: AlertRecord): void {
    this.alertaSeleccionada.set(alerta);
  }

  cerrarModal(): void {
    this.alertaSeleccionada.set(null);
  }
}
