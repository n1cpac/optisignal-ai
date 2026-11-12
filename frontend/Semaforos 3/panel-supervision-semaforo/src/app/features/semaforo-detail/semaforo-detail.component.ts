import { Component, computed, inject } from '@angular/core';
import { DatePipe, PercentPipe } from '@angular/common';

import { EstadoVisual } from '../../core/models/semaforo.model';
import { PanelStateService } from '../../core/services/panel-state.service';
import { TrafficLightComponent } from '../../shared/components/traffic-light/traffic-light.component';
import { ReportFormComponent } from './report-form.component';

@Component({
  selector: 'app-semaforo-detail',
  standalone: true,
  imports: [DatePipe, PercentPipe, TrafficLightComponent, ReportFormComponent],
  template: `
    @if (state.reporteHistorial(); as r) {
      <h2>{{ r.ubicacion }}</h2>
      <p class="historial">
        <span class="estado" [class.verificado]="r.opciones">
          {{ r.opciones ? 'Reporte verificado' : 'No verificado' }}
        </span>
        <small>{{ r.fecha | date: 'dd/MM/yyyy HH:mm' }}</small>
      </p>
      <p class="descripcion">{{ r.descripcion }}</p>
      @if (r.alertasVerificadas) {
        <p class="descripcion verifico">
          Verificó {{ r.alertasVerificadas }} {{ r.alertasVerificadas === 1 ? 'alerta' : 'alertas' }}.
          Última: {{ r.ultimaAlertaVerificada }}
        </p>
      }

      <section class="camara">
        <div class="barra">
          <strong>Escena</strong>
          <button
            type="button"
            [attr.aria-pressed]="state.camaraExpandida()"
            (click)="state.camaraExpandida.set(!state.camaraExpandida())"
          >
            {{ state.camaraExpandida() ? '⤡ Reducir' : '⤢ Expandir' }}
          </button>
        </div>
        <div class="imagen">
          <img [src]="'/reportes/' + r.id + '/escena'" alt="Escena de referencia del reporte (escogida al azar)" />
        </div>
      </section>

      <app-report-form
        [semaforoId]="r.semaforoId"
        [reporteId]="r.id"
        [opciones]="r.opciones"
        (enviado)="state.abrirReporteNuevo($event)"
      />
    } @else { @if (state.seleccionado(); as s) {
      <h2>{{ s.nombre }}</h2>

      <section class="electrico">
        <app-traffic-light [luces]="s.lucesElectricas" />
        <div class="rotulos">
          <strong>Estado semáforo</strong>
          <span>Sistema eléctrico</span>
          <span class="operativo" [class.falla]="s.estadoOperativo === 'anomalia'">
            {{ s.estadoOperativo === 'anomalia' ? 'Anomalía' : 'Normal' }}
          </span>
          <small>Actualizado {{ s.ultimaActualizacion | date: 'HH:mm:ss' }}</small>
        </div>
      </section>

      <section class="camara">
        <div class="barra">
          <strong>Cámara</strong>
          <button
            type="button"
            [attr.aria-pressed]="state.camaraExpandida()"
            (click)="state.camaraExpandida.set(!state.camaraExpandida())"
          >
            {{ state.camaraExpandida() ? '⤡ Reducir' : '⤢ Expandir' }}
          </button>
        </div>

        <div class="imagen">
          <img [src]="imagenSrc()" alt="Imagen en vivo del semáforo" />
        </div>

        <p class="deteccion">
          Detección YOLO: <strong>{{ etiquetasVisual[s.estadoVisual] }}</strong>
          @if (s.confianza != null) {
            <small>· Confianza {{ s.confianza | percent }}</small>
          }
        </p>
      </section>

      <app-report-form [semaforoId]="s.id" />
    } @else {
      <p class="vacio">Selecciona un reporte del historial o un semáforo en el mapa.</p>
    } }
  `,
  styles: [`
    :host { display: flex; flex-direction: column; gap: 16px; }
    h2 { margin: 0; font-size: 18px; }
    .electrico { display: flex; gap: 16px; align-items: flex-start; }
    .rotulos { display: flex; flex-direction: column; gap: 6px; }
    .operativo { color: #76c410; font-weight: 600; }
    .operativo.falla { color: #ff6a5c; }
    small { color: #aaa; }
    .camara { display: flex; flex-direction: column; gap: 8px; }
    .barra { display: flex; justify-content: space-between; align-items: center; }
    .barra button { padding: 4px 10px; font: inherit; font-size: 13px; border: 2px solid #1e6fff; background: #222; color: #fff; cursor: pointer; }
    .imagen { background: #fff; padding: 8px; }
    img { display: block; width: 100%; height: auto; }
    .deteccion { margin: 0; }
    .deteccion small { margin-left: 6px; }
    .historial { display: flex; gap: 10px; align-items: center; margin: 0; }
    .estado { padding: 1px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; background: #8a1f1c; }
    .estado.verificado { background: #2e5e12; }
    .descripcion { margin: 0; font-size: 14px; }
    .descripcion.verifico { font-size: 13px; color: #ccc; }
    .vacio { color: #aaa; }
  `]
})
export class SemaforoDetailComponent {
  protected state = inject(PanelStateService);

  protected readonly etiquetasVisual: Record<EstadoVisual, string> = {
    rojo: 'Rojo',
    amarillo: 'Amarillo',
    verde: 'Verde',
    apagado: 'Apagado',
    multiple: 'Varias luces encendidas',
    sin_deteccion: 'Semáforo no detectado',
    desconocido: 'No se puede determinar',
    sin_senal: 'Sin señal de cámara'
  };

  /** La URL se usa tal cual la entrega el backend (captura nueva o transmision MJPEG). */
  protected imagenSrc = computed(() => this.state.seleccionado()?.imagenUrl ?? '');
}
