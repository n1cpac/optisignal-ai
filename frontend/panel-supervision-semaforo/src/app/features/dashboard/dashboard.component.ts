import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';

import { ApiService } from '../../core/services/api.service';
import { SystemStatus } from '../../core/models/status.model';
import { TrafficLightComponent } from '../../shared/components/traffic-light/traffic-light.component';
import { PageHeadComponent } from '../../shared/components/page-head/page-head.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [DatePipe, TrafficLightComponent, PageHeadComponent],
  template: `
    <app-page-head
      titulo="Panel principal"
      descripcion="Estado del semáforo supervisado, actualizado varias veces por segundo."
      [solapa]="true"
    ></app-page-head>

    <div class="contenedor pagina">
      <section class="consola consola--solapada" aria-label="Estado actual del semáforo">
        <app-traffic-light [estado]="status()?.semaforo ?? null"></app-traffic-light>

        <dl class="consola__filas">
          <div class="consola__fila">
            <dt class="etiqueta">Semáforo detectado</dt>
            <dd>
              <span class="marca" [class]="marcaSemaforo()"></span>
              {{ status()?.semaforo ? nombreSemaforo() : '—' }}
            </dd>
          </div>
          <div class="consola__fila">
            <dt class="etiqueta">Estado operativo</dt>
            <dd>
              <span class="marca" [class]="marcaOperativo()"></span>
              {{ status() ? (status()!.estadoOperativo === 'normal' ? 'Normal' : 'Anomalía') : '—' }}
            </dd>
          </div>
          <div class="consola__fila">
            <dt class="etiqueta">Última actualización</dt>
            <dd>{{ status() ? (status()!.timestampActualizacion | date: 'dd/MM/yyyy HH:mm:ss') : '—' }}</dd>
          </div>
        </dl>
      </section>

      <section class="tiles" aria-label="Indicadores">
        <article class="tile">
          <h2 class="etiqueta">Confianza de detección</h2>
          <div>
            <p class="tile__valor">{{ status() ? status()!.confianzaDeteccion : '—' }}@if (status()) {<small>%</small>}</p>
            <div class="barra" role="progressbar" aria-label="Confianza de detección" aria-valuemin="0" aria-valuemax="100"
                 [attr.aria-valuenow]="status()?.confianzaDeteccion ?? null" style="margin-top: 16px">
              <span class="barra__relleno" [style.width.%]="status()?.confianzaDeteccion ?? 0"></span>
            </div>
          </div>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Alertas acumuladas</h2>
          <p class="tile__valor">{{ status() ? status()!.totalAlertas : '—' }}</p>
        </article>

        <article class="tile">
          <h2 class="etiqueta">Fuente de video</h2>
          <p class="tile__valor tile__valor--texto">
            <span class="marca" [class]="status()?.fuenteVideo === 'conectada' ? 'marca marca--ok' : status() ? 'marca marca--fallo' : 'marca'"></span>
            {{ status() ? (status()!.fuenteVideo === 'conectada' ? 'Conectada' : 'Desconectada') : '—' }}
          </p>
        </article>
      </section>
    </div>
  `
})
export class DashboardComponent {
  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  status = signal<SystemStatus | null>(null);

  nombreSemaforo = computed(() => {
    const s = this.status()?.semaforo;
    return s === 'rojo' ? 'Rojo' : s === 'amarillo' ? 'Amarillo' : s === 'verde' ? 'Verde' : '—';
  });

  marcaSemaforo = computed(() => {
    const s = this.status()?.semaforo;
    return 'marca ' + (s === 'rojo' ? 'marca--fallo' : s === 'amarillo' ? 'marca--aviso' : s === 'verde' ? 'marca--ok' : '');
  });

  marcaOperativo = computed(() => {
    const e = this.status()?.estadoOperativo;
    return 'marca ' + (e === 'normal' ? 'marca--ok' : e === 'anomalia' ? 'marca--fallo' : '');
  });

  constructor() {
    this.api.pollStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((s) => this.status.set(s));
  }
}
