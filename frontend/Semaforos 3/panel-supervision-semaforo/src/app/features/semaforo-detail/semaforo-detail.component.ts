import { Component, computed, inject } from '@angular/core';
import { DatePipe } from '@angular/common';

import { PanelStateService } from '../../core/services/panel-state.service';
import { TrafficLightComponent } from '../../shared/components/traffic-light/traffic-light.component';
import { LiveCameraComponent } from '../../shared/components/live-camera/live-camera.component';
import { ReportFormComponent } from './report-form.component';

@Component({
  selector: 'app-semaforo-detail',
  standalone: true,
  imports: [DatePipe, TrafficLightComponent, LiveCameraComponent, ReportFormComponent],
  template: `
    @if (state.seleccionado(); as s) {
      <h2>{{ s.nombre }}</h2>

      <section class="electrico">
        <app-traffic-light [estado]="s.estadoElectrico" />
        <div class="rotulos">
          <strong>Estado semáforo</strong>
          <span>Sistema eléctrico</span>
          <span class="operativo" [class.falla]="s.estadoOperativo === 'anomalia'">
            {{ s.estadoOperativo === 'anomalia' ? 'Anomalía' : 'Normal' }}
          </span>
          <small>Actualizado {{ s.ultimaActualizacion | date: 'HH:mm:ss' }}</small>
        </div>
      </section>

      <section class="imagen">
        @if (s.fuenteImagen === 'obs') {
          <app-live-camera etiquetaDispositivo="OBS" />
        } @else {
          <img [src]="imagenSrc()" alt="Imagen en vivo del semáforo" />
        }
      </section>

      <app-report-form [semaforoId]="s.id" />
    } @else {
      <p class="vacio">Selecciona un reporte del historial o un semáforo en el mapa.</p>
    }
  `,
  styles: [`
    :host { display: flex; flex-direction: column; gap: 16px; }
    h2 { margin: 0; font-size: 18px; }
    .electrico { display: flex; gap: 16px; align-items: flex-start; }
    .rotulos { display: flex; flex-direction: column; gap: 6px; }
    .operativo { color: #76c410; font-weight: 600; }
    .operativo.falla { color: #ff6a5c; }
    small { color: #aaa; }
    .imagen { background: #fff; padding: 8px; }
    img { display: block; width: 100%; height: auto; }
    .vacio { color: #aaa; }
  `]
})
export class SemaforoDetailComponent {
  protected state = inject(PanelStateService);

  /** La URL se usa tal cual la entrega el backend (captura nueva o transmision MJPEG). */
  protected imagenSrc = computed(() => this.state.seleccionado()?.imagenUrl ?? '');
}
