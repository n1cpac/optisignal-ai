import { Component, computed, inject } from '@angular/core';

import { PanelStateService } from '../../core/services/panel-state.service';
import { ReportItemComponent } from '../../shared/components/report-item/report-item.component';

@Component({
  selector: 'app-report-history',
  standalone: true,
  imports: [ReportItemComponent],
  template: `
    <h2>Historial de reportes</h2>

    @for (reporte of reportes(); track reporte.id) {
      <app-report-item
        [reporte]="reporte"
        [seleccionado]="reporte.semaforoId === state.seleccionadoId()"
        (seleccionar)="state.seleccionar(reporte.semaforoId)"
      />
    } @empty {
      <p class="vacio">Sin reportes.</p>
    }
  `,
  styles: [`
    :host { display: block; }
    h2 { margin: 0; padding: 16px 12px; font-size: 20px; }
    .vacio { padding: 0 12px; color: #aaa; }
  `]
})
export class ReportHistoryComponent {
  protected state = inject(PanelStateService);

  /** Mas recientes primero. */
  protected reportes = computed(() =>
    [...this.state.reportes()].sort((a, b) => b.fecha.localeCompare(a.fecha))
  );
}
