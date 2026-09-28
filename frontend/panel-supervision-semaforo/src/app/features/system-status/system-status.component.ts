import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ApiService } from '../../core/services/api.service';
import { SystemStatus } from '../../core/models/status.model';
import { PageHeadComponent } from '../../shared/components/page-head/page-head.component';

@Component({
  selector: 'app-system-status',
  standalone: true,
  imports: [PageHeadComponent],
  template: `
    <app-page-head
      titulo="Información del sistema"
      descripcion="Recursos del equipo y estado de la fuente de video."
    ></app-page-head>

    <div class="contenedor pagina">
      <section class="tiles" aria-label="Estado del sistema">
        <article class="tile">
          <h2 class="etiqueta">Fuente de video</h2>
          <p class="tile__valor tile__valor--texto">
            <span class="marca" [class]="status()?.fuenteVideo === 'conectada' ? 'marca marca--ok' : status() ? 'marca marca--fallo' : 'marca'"></span>
            {{ status() ? (status()!.fuenteVideo === 'conectada' ? 'Conectada' : 'Desconectada') : '—' }}
          </p>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Cuadros por segundo</h2>
          <p class="tile__valor">{{ status() ? status()!.fps : '—' }}@if (status()) {<small>fps</small>}</p>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Uso de CPU</h2>
          <div>
            <p class="tile__valor">{{ status() ? status()!.usoCpu : '—' }}@if (status()) {<small>%</small>}</p>
            <div class="barra" role="progressbar" aria-label="Uso de CPU" aria-valuemin="0" aria-valuemax="100"
                 [attr.aria-valuenow]="status()?.usoCpu ?? null" style="margin-top: 16px">
              <span class="barra__relleno" [style.width.%]="status()?.usoCpu ?? 0"></span>
            </div>
          </div>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Uso de memoria</h2>
          <div>
            <p class="tile__valor">{{ status() ? status()!.usoMemoria : '—' }}@if (status()) {<small>%</small>}</p>
            <div class="barra" role="progressbar" aria-label="Uso de memoria" aria-valuemin="0" aria-valuemax="100"
                 [attr.aria-valuenow]="status()?.usoMemoria ?? null" style="margin-top: 16px">
              <span class="barra__relleno" [style.width.%]="status()?.usoMemoria ?? 0"></span>
            </div>
          </div>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Alertas acumuladas</h2>
          <p class="tile__valor">{{ status() ? status()!.totalAlertas : '—' }}</p>
        </article>
      </section>
    </div>
  `
})
export class SystemStatusComponent {
  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  status = signal<SystemStatus | null>(null);

  constructor() {
    this.api.pollStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((s) => this.status.set(s));
  }
}
