import { Component, computed, inject, signal } from '@angular/core';

import { Reporte, VistaReportes } from '../../core/models/reporte.model';
import { ApiService } from '../../core/services/api.service';
import { PanelStateService } from '../../core/services/panel-state.service';
import { ReportItemComponent } from '../../shared/components/report-item/report-item.component';

@Component({
  selector: 'app-report-history',
  standalone: true,
  imports: [ReportItemComponent],
  template: `
    <div class="pestanas" role="tablist" aria-label="Reportes">
      <button
        id="tab-actuales"
        type="button"
        role="tab"
        aria-controls="panel-reportes"
        [attr.aria-selected]="pestana() === 'actuales'"
        [attr.tabindex]="pestana() === 'actuales' ? 0 : -1"
        (click)="verActuales()"
        (keydown.arrowRight)="cambiar('historial', $event)"
        (keydown.arrowLeft)="cambiar('historial', $event)"
      >
        Actuales
        <span class="contador" [class.aviso]="state.hayAlertaNueva()">{{ state.actuales().total }}</span>
      </button>
      <button
        id="tab-historial"
        type="button"
        role="tab"
        aria-controls="panel-reportes"
        [attr.aria-selected]="pestana() === 'historial'"
        [attr.tabindex]="pestana() === 'historial' ? 0 : -1"
        (click)="pestana.set('historial')"
        (keydown.arrowRight)="cambiar('actuales', $event)"
        (keydown.arrowLeft)="cambiar('actuales', $event)"
      >
        Historial
      </button>
    </div>

    <p class="solo-lector" aria-live="polite">
      @if (state.hayAlertaNueva()) { Nueva alerta en los reportes actuales. }
    </p>

    <div id="panel-reportes" role="tabpanel" [attr.aria-labelledby]="'tab-' + pestana()">
      @for (reporte of pagina().items; track reporte.id) {
        <app-report-item
          [reporte]="reporte"
          [detalle]="pestana() === 'historial'"
          [nueva]="pestana() === 'actuales' && state.alertasNuevas().has(reporte.semaforoId)"
          [seleccionado]="
            pestana() === 'historial'
              ? reporte.id === state.reporteHistorial()?.id
              : reporte.semaforoId === state.seleccionadoId()
          "
          (seleccionar)="abrir(reporte)"
        />
      } @empty {
        <p class="vacio">
          {{ pestana() === 'actuales' ? 'No hay alertas pendientes de hoy.' : 'Sin reportes en el historial.' }}
        </p>
      }

      @if (totalPaginas() > 1) {
        <nav class="paginacion" aria-label="Páginas de reportes">
          <button type="button" [disabled]="numeroPagina() === 1" (click)="irA(numeroPagina() - 1)">‹ Anterior</button>
          <span aria-live="polite">Página {{ numeroPagina() }} de {{ totalPaginas() }}</span>
          <button type="button" [disabled]="numeroPagina() === totalPaginas()" (click)="irA(numeroPagina() + 1)">Siguiente ›</button>
        </nav>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .pestanas { display: flex; gap: var(--sp-1); padding: var(--sp-1); margin-bottom: var(--sp-3); background: var(--bg); border-radius: var(--r-control); }
    .pestanas button {
      display: inline-flex;
      flex: 1;
      align-items: center;
      justify-content: center;
      gap: var(--sp-2);
      min-height: 36px;
      padding: 0 var(--sp-2);
      border: 0;
      border-radius: 6px;
      background: transparent;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .pestanas button[aria-selected='true'] { background: var(--border); color: var(--text); }
    .pestanas button:hover { color: var(--text); }
    .contador { min-width: 20px; padding: 0 6px; border-radius: var(--r-pill); background: var(--danger); color: var(--on-accent); font-family: var(--font-mono); font-size: 12px; font-weight: 500; }
    .contador.aviso { box-shadow: 0 0 0 3px var(--warning); animation: latido 1s ease-in-out infinite; }
    @keyframes latido { 50% { transform: scale(1.25); } }
    @media (prefers-reduced-motion: reduce) { .contador.aviso { animation: none; } }
    .solo-lector { position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); }
    .vacio { margin: 0; padding: var(--sp-3); color: var(--text-muted); }
    .paginacion { display: flex; justify-content: space-between; align-items: center; gap: 6px; padding: var(--sp-3) 0 0; font-size: 13px; color: var(--text-muted); }
    .paginacion button { min-height: 36px; padding: 0 var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-control); background: var(--bg); color: var(--text); font-size: 13px; cursor: pointer; }
    .paginacion button:hover:not(:disabled) { border-color: var(--accent); }
    .paginacion button:disabled { opacity: 0.4; cursor: not-allowed; }
  `]
})
export class ReportHistoryComponent {
  protected state = inject(PanelStateService);
  private api = inject(ApiService);
  protected pestana = signal<VistaReportes>('actuales');

  protected pagina = computed(() =>
    this.pestana() === 'actuales' ? this.state.actuales() : this.state.historial()
  );
  private paginaSeleccionada = computed(() =>
    this.pestana() === 'actuales' ? this.state.paginaActuales : this.state.paginaHistorial
  );
  protected numeroPagina = computed(() => this.paginaSeleccionada()());
  protected totalPaginas = computed(() =>
    Math.max(1, Math.ceil(this.pagina().total / this.pagina().tamano))
  );

  protected irA(numero: number): void {
    this.paginaSeleccionada().set(numero);
  }

  /** Seleccionar el semaforo y, si es una alerta, avisar que se abrio (frena los recordatorios). */
  protected abrir(reporte: Reporte): void {
    if (this.pestana() === 'historial') {
      this.state.verReporteHistorial(reporte); // sin mover el mapa
      return;
    }
    this.state.seleccionar(reporte.semaforoId);
    if (!reporte.automatica) return;
    this.state.marcarVista(reporte.semaforoId);
    this.api.abrirAlerta(reporte.id).subscribe({ error: () => undefined });
  }

  protected verActuales(): void {
    this.pestana.set('actuales');
    this.state.paginaActuales.set(1); // las alertas nuevas llegan al principio de la cola
  }

  /** Flechas: pasa a la otra pestana y le da el foco, como en el patron de pestanas accesibles. */
  protected cambiar(destino: VistaReportes, evento: Event): void {
    this.pestana.set(destino);
    document.getElementById(`tab-${destino}`)?.focus();
    evento.preventDefault();
  }
}
