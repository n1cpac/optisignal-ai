import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { Destinatario, OpcionesReporte, TipoFalla } from '../../core/models/reporte.model';
import { ZONA_BOGOTA } from '../../shared/hora-bogota';

type EstadoEnvio = 'inactivo' | 'enviando' | 'enviado' | 'error';

@Component({
  selector: 'app-report-form',
  standalone: true,
  imports: [DatePipe, FormsModule],
  template: `
    <form class="reporte" (ngSubmit)="enviar()">
      <h3>{{ opciones ? 'Reporte verificado' : 'Reporte' }}</h3>
      @if (opciones) {
        <p class="aviso">Verificado el {{ opciones.fecha | date: 'dd/MM/yyyy HH:mm' : zona }}. Solo lectura.</p>
      }

      <!-- Un fieldset deshabilitado bloquea todos los campos de un reporte ya verificado -->
      <fieldset class="campos" [disabled]="!!opciones">
        <fieldset>
          <legend>La detección eléctrica, ¿coincide con la imagen?</legend>
          <div class="segmentado">
            <label><input type="radio" name="coincide" [value]="true" [(ngModel)]="coincide" /><span>Coincide</span></label>
            <label><input type="radio" name="coincide" [value]="false" [(ngModel)]="coincide" /><span>No coincide</span></label>
          </div>
        </fieldset>

        <fieldset>
          <legend>¿Hay un fallo en el semáforo?</legend>
          <div class="segmentado">
            <label><input type="radio" name="falla" [value]="true" [(ngModel)]="falla" /><span>Fallo en el semáforo</span></label>
            <label><input type="radio" name="falla" [value]="false" [(ngModel)]="falla" /><span>No hay fallo</span></label>
          </div>
        </fieldset>

        @if (falla) {
          <fieldset>
            <legend>Tipo de reporte de falla</legend>
            <div class="segmentado">
              <label>
                <input type="radio" name="tipoFalla" [value]="'funcionamiento'" [(ngModel)]="tipoFalla" />
                <span>Por funcionamiento (secuencia o intermitencia)</span>
              </label>
              <label>
                <input type="radio" name="tipoFalla" [value]="'dano'" [(ngModel)]="tipoFalla" />
                <span>Por daño (apagado o daño físico)</span>
              </label>
            </div>
          </fieldset>

          <fieldset>
            <legend>Semáforos con falla (numeración de izquierda a derecha en cámara)</legend>
            <div class="opciones">
              @for (num of numerosSemaforos; track num) {
                <label class="casilla">
                  <input type="checkbox" [name]="'sem_' + num" [(ngModel)]="semaforosSeleccionados[num]" />
                  <span>Semáforo #{{ num }}</span>
                </label>
              }
            </div>
          </fieldset>

          <fieldset>
            <legend>Enviar a (opcional)</legend>
            <div class="opciones">
              <label class="casilla"><input type="checkbox" name="transito" [(ngModel)]="destinatarios.transito" /><span>Policía de tránsito</span></label>
              <label class="casilla"><input type="checkbox" name="tecnicos" [(ngModel)]="destinatarios.tecnicos" /><span>Técnicos de reparación</span></label>
            </div>
          </fieldset>
        }

        <label class="observaciones">
          <span class="etiqueta">Observaciones</span>
          <textarea name="comentario" rows="4" placeholder="Escribe el reporte..." [(ngModel)]="comentario"></textarea>
        </label>
      </fieldset>

      @if (!opciones) {
        <button type="submit" class="primario" [disabled]="!puedeEnviar">Enviar reporte</button>
      }

      <div role="status">
        @if (estado === 'enviando') { <p class="aviso">Enviando...</p> }
        @if (estado === 'enviado') { <p class="aviso ok">Reporte enviado.</p> }
        @if (estado === 'error') { <p class="aviso error">No se pudo enviar. Intenta de nuevo.</p> }
      </div>
    </form>
  `,
  styles: [`
    .reporte {
      display: flex;
      flex-direction: column;
      gap: var(--sp-3);
      padding: var(--sp-4);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-panel);
    }
    h3 { margin: 0; font-family: var(--font-display); font-size: 16px; font-weight: 600; }
    fieldset { border: 0; margin: 0; padding: 0; min-width: 0; display: flex; flex-direction: column; gap: var(--sp-2); }
    .campos { gap: var(--sp-4); }
    legend { padding: 0; margin-bottom: var(--sp-2); font-size: 13px; font-weight: 500; color: var(--text-muted); }

    /* Radios reales, ocultos a la vista pero con foco y teclado */
    .segmentado input, .casilla input {
      position: absolute;
      width: 1px;
      height: 1px;
      margin: -1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      opacity: 0;
    }
    .segmentado { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-1); padding: var(--sp-1); background: var(--bg); border: 1px solid var(--border); border-radius: var(--r-control); }
    .segmentado label { position: relative; display: flex; }
    .segmentado span {
      display: flex;
      flex: 1;
      align-items: center;
      justify-content: center;
      min-height: 36px;
      padding: 4px var(--sp-2);
      border-radius: 6px;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 500;
      text-align: center;
      cursor: pointer;
    }
    .segmentado label:hover span { color: var(--text); }
    .segmentado input:checked + span { background: var(--accent); color: var(--on-accent); font-weight: 600; }
    .segmentado input:focus-visible + span, .casilla input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }

    .opciones { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
    .casilla { position: relative; display: inline-flex; }
    .casilla span {
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      padding: 0 var(--sp-3);
      border: 1px solid var(--border);
      border-radius: var(--r-control);
      background: var(--bg);
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
    }
    .casilla input:checked + span { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--accent); }
    .casilla input:checked + span::before { content: '✓ '; white-space: pre; }

    /* Reporte ya verificado: se resalta la opcion marcada para que se lea */
    .campos:disabled .segmentado span, .campos:disabled .casilla span { cursor: default; opacity: 0.6; }
    .campos:disabled .segmentado input:checked + span, .campos:disabled .casilla input:checked + span { opacity: 1; }

    .observaciones { display: flex; flex-direction: column; gap: var(--sp-2); }
    .etiqueta { font-size: 13px; font-weight: 500; color: var(--text-muted); }
    textarea {
      width: 100%;
      min-height: 88px;
      resize: vertical;
      padding: var(--sp-2) var(--sp-3);
      border: 1px solid var(--border);
      border-radius: var(--r-control);
      background: var(--bg);
      color: var(--text);
      font: inherit;
    }
    textarea::placeholder { color: var(--text-muted); }
    .primario {
      width: 100%;
      min-height: 44px;
      border: 0;
      border-radius: var(--r-control);
      background: var(--accent);
      color: var(--on-accent);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    .primario:disabled { opacity: 0.5; cursor: not-allowed; }
    .aviso { margin: 0; font-size: 13px; color: var(--text-muted); }
    .aviso.ok { color: var(--ok); }
    .aviso.error { color: var(--danger); }
  `]
})
export class ReportFormComponent implements OnChanges {
  /** Al cambiar de semaforo o de reporte el formulario se limpia. */
  @Input({ required: true }) semaforoId!: string;
  @Input() reporteId: string | null = null;
  @Input() cantidadSemaforos = 1;
  /** Opciones de un reporte ya verificado: el formulario las muestra en solo lectura. */
  @Input() opciones: OpcionesReporte | null = null;
  /** Id del reporte recien creado. */
  @Output() enviado = new EventEmitter<string>();

  private api = inject(ApiService);
  protected readonly zona = ZONA_BOGOTA;

  coincide: boolean | null = null;
  falla: boolean | null = null;
  tipoFalla: TipoFalla | null = null;
  semaforosSeleccionados: Record<number, boolean> = { 1: true };
  comentario = '';
  destinatarios = { transito: false, tecnicos: false };
  estado: EstadoEnvio = 'inactivo';

  get numerosSemaforos(): number[] {
    const maxNum = Math.max(
      this.cantidadSemaforos || 1,
      ...(this.opciones?.semaforosAfectados ?? [1]),
      1
    );
    return Array.from({ length: maxNum }, (_, i) => i + 1);
  }

  get puedeEnviar(): boolean {
    if (this.coincide === null || this.falla === null || this.estado === 'enviando') {
      return false;
    }
    if (this.falla) {
      const haySemaforo = this.numerosSemaforos.some((n) => !!this.semaforosSeleccionados[n]);
      return this.tipoFalla !== null && haySemaforo;
    }
    return true;
  }

  ngOnChanges(changes: SimpleChanges): void {
    const cambioObjetivo = !!changes['semaforoId'] || !!changes['reporteId'] || !!changes['opciones'];
    if (!cambioObjetivo && !this.opciones) {
      if ((this.cantidadSemaforos || 1) === 1 && !Object.keys(this.semaforosSeleccionados).length) {
        this.semaforosSeleccionados = { 1: true };
      }
      return;
    }

    this.estado = 'inactivo';
    if (!this.opciones) {
      this.reiniciar();
      return;
    }
    this.coincide = this.opciones.coincide;
    this.falla = this.opciones.falla;
    this.tipoFalla = this.opciones.tipoFalla ?? null;
    const seleccionados: Record<number, boolean> = {};
    for (const n of this.opciones.semaforosAfectados ?? []) {
      seleccionados[n] = true;
    }
    this.semaforosSeleccionados = seleccionados;
    this.comentario = this.opciones.comentario ?? '';
    this.destinatarios = {
      transito: this.opciones.destinatarios.includes('transito'),
      tecnicos: this.opciones.destinatarios.includes('tecnicos')
    };
  }

  enviar(): void {
    if (!this.puedeEnviar || this.coincide === null || this.falla === null) return;

    // Los destinatarios y detalle de falla solo aplican cuando hay fallo en el semaforo
    const destinatarios: Destinatario[] = [];
    if (this.falla && this.destinatarios.transito) destinatarios.push('transito');
    if (this.falla && this.destinatarios.tecnicos) destinatarios.push('tecnicos');

    const semaforosAfectados = this.falla
      ? this.numerosSemaforos.filter((n) => !!this.semaforosSeleccionados[n])
      : [];
    const tipoFalla = this.falla ? this.tipoFalla : null;

    this.estado = 'enviando';
    this.api
      .enviarReporte({
        semaforoId: this.semaforoId,
        coincide: this.coincide,
        falla: this.falla,
        comentario: this.comentario.trim(),
        destinatarios,
        tipoFalla,
        semaforosAfectados
      })
      .subscribe({
        next: ({ id }) => {
          this.reiniciar();
          this.estado = 'enviado';
          this.enviado.emit(id);
        },
        error: () => (this.estado = 'error')
      });
  }

  private reiniciar(): void {
    this.coincide = null;
    this.falla = null;
    this.tipoFalla = null;
    this.semaforosSeleccionados = (this.cantidadSemaforos || 1) === 1 ? { 1: true } : {};
    this.comentario = '';
    this.destinatarios = { transito: false, tecnicos: false };
  }
}
