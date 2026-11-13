import { Component, computed, inject } from '@angular/core';
import { DatePipe, UpperCasePipe } from '@angular/common';

import { EstadoLuz, EstadoVisual } from '../../core/models/semaforo.model';
import { PanelStateService } from '../../core/services/panel-state.service';
import { horaBogota, ZONA_BOGOTA } from '../../shared/hora-bogota';
import { TrafficLightComponent } from '../../shared/components/traffic-light/traffic-light.component';
import { ReportFormComponent } from './report-form.component';

@Component({
  selector: 'app-semaforo-detail',
  standalone: true,
  imports: [DatePipe, UpperCasePipe, TrafficLightComponent, ReportFormComponent],
  template: `
    @if (state.reporteHistorial(); as r) {
      <section class="tarjeta">
        <div class="titulo-fila">
          <div>
            <span class="sobretitulo">INTERSECCIÓN</span>
            <h2>{{ r.ubicacion }}</h2>
          </div>
          <span class="badge" [class.ok]="r.opciones" [class.falla]="!r.opciones">
            {{ r.opciones ? 'Reporte verificado' : 'No verificado' }}
          </span>
        </div>
        <small class="mono">{{ r.fecha | date: 'dd/MM/yyyy HH:mm' : zona }}</small>
        <p class="descripcion">{{ r.descripcion }}</p>
        @if (r.alertasVerificadas) {
          <p class="descripcion verifico">
            Verificó {{ r.alertasVerificadas }} {{ r.alertasVerificadas === 1 ? 'alerta' : 'alertas' }}.
            Última: {{ r.ultimaAlertaVerificada }}
          </p>
        }
      </section>

      <section class="tarjeta">
        <div class="titulo-fila">
          <h3>Escena</h3>
          <button
            type="button"
            class="expandir"
            [attr.aria-pressed]="state.camaraExpandida()"
            (click)="state.camaraExpandida.set(!state.camaraExpandida())"
          >
            {{ state.camaraExpandida() ? '⤡ Reducir' : '⤢ Expandir' }}
          </button>
        </div>
        <div class="visor">
          <img [src]="'/reportes/' + r.id + '/escena'" alt="Escena de referencia del reporte (escogida al azar)" />
        </div>
      </section>

      <app-report-form
        [semaforoId]="r.semaforoId"
        [reporteId]="r.id"
        [cantidadSemaforos]="cantidadCabezales(r.semaforoId)"
        [opciones]="r.opciones"
        (enviado)="state.abrirReporteNuevo($event)"
      />
    } @else { @if (state.seleccionado(); as s) {
      <section class="tarjeta">
        <div class="titulo-fila">
          <div>
            <span class="sobretitulo">INTERSECCIÓN</span>
            <h2>{{ s.nombre }}</h2>
          </div>
          <span class="badge" [class.falla]="s.estadoOperativo === 'anomalia'" [class.ok]="s.estadoOperativo !== 'anomalia'">
            {{ s.estadoOperativo === 'anomalia' ? 'ANOMALÍA' : 'NORMAL' }}
          </span>
        </div>

        <div class="electrico">
          <app-traffic-light [ciclo]="grafico().ciclo" [luces]="grafico().luces" [parpadeo]="grafico().parpadeo" />
          <dl class="filas">
            <div class="fila">
              <dt>Sistema eléctrico</dt>
              <dd class="valor" [class.c-falla]="s.estadoOperativo === 'anomalia'" [class.c-ok]="s.estadoOperativo !== 'anomalia'">
                {{ s.estadoOperativo === 'anomalia' ? 'Anomalía' : 'Normal' }}
              </dd>
            </div>
            <div class="fila">
              <dt>Detección YOLO</dt>
              <dd class="valor" [class]="'c-' + s.estadoVisual">{{ etiquetasVisual[s.estadoVisual] }}</dd>
              @if (s.confianza != null) {
                <div
                  class="barra"
                  role="progressbar"
                  aria-label="Confianza de la detección"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  [attr.aria-valuenow]="porcentaje(s.confianza)"
                  [class]="'c-' + s.estadoVisual"
                >
                  <span [style.width.%]="porcentaje(s.confianza)"></span>
                </div>
                <small class="mono">
                  Confianza {{ porcentaje(s.confianza) }} %@if (primerCabezal(); as c) { · #{{ c.numero }} {{ etiquetasVisual[c.estadoVisual] }}}
                </small>
              }
            </div>
            <div class="fila">
              <dt>Actualizado</dt>
              <dd class="mono">{{ hora(s.ultimaActualizacion) }}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section class="tarjeta">
        <div class="titulo-fila">
          <h3>Cámara</h3>
          <button
            type="button"
            class="expandir"
            [attr.aria-pressed]="state.camaraExpandida()"
            (click)="state.camaraExpandida.set(!state.camaraExpandida())"
          >
            {{ state.camaraExpandida() ? '⤡ Reducir' : '⤢ Expandir' }}
          </button>
        </div>

        <div class="visor">
          @if (s.estadoVisual === 'sin_senal') {
            <p class="sin-senal">Sin señal</p>
          } @else {
            <img [src]="imagenSrc()" alt="Imagen en vivo del semáforo" />
            <span class="rotulo en-vivo"><i class="punto-vivo"></i>EN VIVO</span>
            <span class="rotulo cam-id mono">CAM-{{ s.id | uppercase }} · {{ hora(s.ultimaActualizacion) }}</span>
          }
        </div>

        @if (s.cabezales?.length) {
          <div class="cabezales">
            @for (c of s.cabezales; track c.numero) {
              <span class="cabezal" [class.alerta]="!!c.anomalia">
                <strong>#{{ c.numero }}</strong>: {{ etiquetasVisual[c.estadoVisual] }}
              </span>
            }
          </div>
        }
      </section>

      <app-report-form
        [semaforoId]="s.id"
        [cantidadSemaforos]="s.cabezales?.length || 1"
        (enviado)="state.reporteEnviadoEnVivo(s.id)"
      />
    } @else {
      <p class="vacio">Selecciona un reporte del historial o un semáforo en el mapa.</p>
    } }
  `,
  styles: [`
    :host { display: flex; flex-direction: column; gap: var(--sp-3); }
    .tarjeta { display: flex; flex-direction: column; gap: var(--sp-3); padding: var(--sp-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-panel); }
    .titulo-fila { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--sp-3); }
    .sobretitulo { display: block; color: var(--text-muted); font-size: 12px; font-weight: 500; letter-spacing: 0.08em; }
    h2 { margin: 0; font-family: var(--font-display); font-size: 22px; font-weight: 600; }
    h3 { margin: 0; font-family: var(--font-display); font-size: 16px; font-weight: 600; }
    .mono { font-family: var(--font-mono); }
    small { color: var(--text-muted); font-size: 12px; }
    .badge { flex: none; padding: 3px 10px; border: 1px solid var(--border); border-radius: var(--r-pill); font-size: 12px; font-weight: 600; letter-spacing: 0.04em; }
    .badge.falla { color: var(--danger); background: color-mix(in srgb, var(--danger) 14%, transparent); border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
    .badge.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 10%, transparent); border-color: color-mix(in srgb, var(--ok) 35%, transparent); }

    .electrico { display: flex; gap: var(--sp-4); align-items: flex-start; }
    .filas { display: flex; flex: 1; flex-direction: column; gap: var(--sp-3); min-width: 0; margin: 0; }
    .fila { display: flex; flex-direction: column; gap: 4px; }
    dt { color: var(--text-muted); font-size: 12px; font-weight: 500; }
    dd { margin: 0; }
    .valor { font-size: 15px; font-weight: 600; }
    .c-falla, .c-rojo, .c-multiple { color: var(--danger); }
    .c-ok, .c-verde { color: var(--ok); }
    .c-amarillo, .c-amarillo_intermitente { color: var(--warning); }
    .c-apagado, .c-sin_deteccion, .c-desconocido, .c-sin_senal { color: var(--text-muted); }
    .barra { height: 6px; border-radius: var(--r-pill); background: var(--border); overflow: hidden; }
    .barra span { display: block; height: 100%; border-radius: var(--r-pill); background: currentColor; }

    .expandir { min-height: 36px; padding: 0 var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-control); background: transparent; color: var(--accent); font-size: 13px; font-weight: 500; cursor: pointer; }
    .expandir:hover { border-color: var(--accent); }
    .visor { position: relative; aspect-ratio: 16 / 9; overflow: hidden; border-radius: var(--r-control); background: var(--surface-deep); }
    .visor img { display: block; width: 100%; height: 100%; object-fit: contain; }
    .rotulo { position: absolute; padding: 3px 8px; border-radius: var(--r-chip); background: color-mix(in srgb, black 80%, transparent); color: var(--text); font-size: 12px; font-weight: 600; }
    .en-vivo { top: var(--sp-2); left: var(--sp-2); display: inline-flex; align-items: center; gap: 6px; letter-spacing: 0.04em; }
    .punto-vivo { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); }
    .cam-id { right: var(--sp-2); bottom: var(--sp-2); font-weight: 400; }
    .sin-senal { display: flex; align-items: center; justify-content: center; height: 100%; margin: 0; color: var(--text-muted); }

    .cabezales { display: flex; flex-wrap: wrap; gap: 6px; }
    .cabezal { padding: 2px 8px; border: 1px solid var(--border); border-radius: var(--r-chip); background: var(--chip-bg); color: var(--text); font-size: 12px; }
    .cabezal.alerta { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 40%, transparent); background: color-mix(in srgb, var(--danger) 14%, transparent); }
    .descripcion { margin: 0; font-size: 14px; }
    .descripcion.verifico { font-size: 13px; color: var(--text-muted); }
    .vacio { color: var(--text-muted); }
  `]
})
export class SemaforoDetailComponent {
  protected state = inject(PanelStateService);

  protected readonly etiquetasVisual: Record<EstadoVisual, string> = {
    rojo: 'Rojo',
    amarillo: 'Amarillo',
    amarillo_intermitente: 'Amarillo intermitente (Falla)',
    verde: 'Verde',
    apagado: 'Apagado',
    multiple: 'Varias luces encendidas',
    sin_deteccion: 'Semáforo no detectado',
    desconocido: 'No se puede determinar',
    sin_senal: 'Sin señal de cámara'
  };

  /** La URL se usa tal cual la entrega el backend (captura nueva o transmision MJPEG). */
  protected imagenSrc = computed(() => this.state.seleccionado()?.imagenUrl ?? '');

  /** Normal: ciclo de un semaforo funcional. Anomalia: lo que YOLO ve en el semaforo #1. */
  protected grafico = computed(() => {
    const s = this.state.seleccionado();
    const sinLuces = { ciclo: false, luces: [] as EstadoLuz[], parpadeo: null as EstadoLuz | null };
    if (!s) return sinLuces;
    if (s.estadoOperativo === 'normal') return { ...sinLuces, ciclo: true };
    const visual = (s.cabezales?.find((c) => c.numero === 1) ?? s.cabezales?.[0])?.estadoVisual ?? s.estadoVisual;
    switch (visual) {
      case 'rojo':
      case 'amarillo':
      case 'verde':
        return { ...sinLuces, luces: [visual] };
      case 'amarillo_intermitente':
        return { ...sinLuces, parpadeo: 'amarillo' as const };
      case 'multiple': // shortcut: la lista de luces es del semaforo, no del #1; ajustar si el backend la da por cabezal
        return { ...sinLuces, luces: s.lucesDetectadas };
      default: // apagado, sin_deteccion, desconocido, sin_senal: no hay luz que mostrar
        return sinLuces;
    }
  });

  protected readonly zona = ZONA_BOGOTA;
  protected hora = horaBogota;
  protected porcentaje = (confianza: number): number => Math.round(confianza * 100);

  protected primerCabezal = computed(() => {
    const cabezales = this.state.seleccionado()?.cabezales;
    return cabezales?.find((c) => c.numero === 1) ?? cabezales?.[0] ?? null;
  });

  protected cantidadCabezales(semaforoId: string): number {
    return this.state.semaforos().find((x) => x.id === semaforoId)?.cabezales?.length || 1;
  }
}
