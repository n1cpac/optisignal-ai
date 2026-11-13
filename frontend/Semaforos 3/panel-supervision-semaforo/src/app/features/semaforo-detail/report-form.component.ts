import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { Destinatario, OpcionesReporte, TipoFalla } from '../../core/models/reporte.model';

type EstadoEnvio = 'inactivo' | 'enviando' | 'enviado' | 'error';

@Component({
  selector: 'app-report-form',
  standalone: true,
  imports: [DatePipe, FormsModule],
  template: `
    <form class="reporte" (ngSubmit)="enviar()">
      <h3>{{ opciones ? 'Reporte verificado' : 'Reporte' }}</h3>
      @if (opciones) {
        <p class="aviso">Verificado el {{ opciones.fecha | date: 'dd/MM/yyyy HH:mm' }}. Solo lectura.</p>
      }

      <!-- Un fieldset deshabilitado bloquea todos los campos de un reporte ya verificado -->
      <fieldset class="campos" [disabled]="!!opciones">
      <fieldset>
        <legend>La detección eléctrica, ¿coincide con la imagen?</legend>
        <label><input type="radio" name="coincide" [value]="true" [(ngModel)]="coincide" /> Coincide</label>
        <label><input type="radio" name="coincide" [value]="false" [(ngModel)]="coincide" /> No coincide</label>
      </fieldset>

      <fieldset>
        <legend>¿Hay un fallo en el semáforo?</legend>
        <label><input type="radio" name="falla" [value]="true" [(ngModel)]="falla" /> Fallo en el semáforo</label>
        <label><input type="radio" name="falla" [value]="false" [(ngModel)]="falla" /> No hay fallo</label>
      </fieldset>

      @if (falla) {
        <fieldset>
          <legend>Tipo de reporte de falla</legend>
          <label>
            <input type="radio" name="tipoFalla" [value]="'funcionamiento'" [(ngModel)]="tipoFalla" />
            Por funcionamiento (secuencia o intermitencia)
          </label>
          <label>
            <input type="radio" name="tipoFalla" [value]="'dano'" [(ngModel)]="tipoFalla" />
            Por daño (apagado o daño físico)
          </label>
        </fieldset>

        <fieldset>
          <legend>Semáforos con falla (numeración de izquierda a derecha en cámara)</legend>
          <div class="semaforos-grid">
            @for (num of numerosSemaforos; track num) {
              <label>
                <input type="checkbox" [name]="'sem_' + num" [(ngModel)]="semaforosSeleccionados[num]" />
                Semáforo #{{ num }}
              </label>
            }
          </div>
        </fieldset>

        <fieldset>
          <legend>Enviar a (opcional)</legend>
          <label><input type="checkbox" name="transito" [(ngModel)]="destinatarios.transito" /> Policía de tránsito</label>
          <label><input type="checkbox" name="tecnicos" [(ngModel)]="destinatarios.tecnicos" /> Técnicos de reparación</label>
        </fieldset>
      }

      <textarea
        name="comentario"
        rows="4"
        placeholder="Escribe el reporte..."
        [(ngModel)]="comentario"
      ></textarea>
      </fieldset>

      @if (!opciones) {
        <button type="submit" [disabled]="!puedeEnviar">Enviar ▶</button>
      }

      @if (estado === 'enviando') { <p class="aviso">Enviando...</p> }
      @if (estado === 'enviado') { <p class="aviso">Reporte enviado.</p> }
      @if (estado === 'error') { <p class="aviso error">No se pudo enviar. Intenta de nuevo.</p> }
    </form>
  `,
  styles: [`
    .reporte { display: flex; flex-direction: column; gap: 10px; border: 2px solid #fff; padding: 12px; }
    h3 { margin: 0; font-size: 20px; }
    fieldset { border: 0; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
    .semaforos-grid { display: flex; flex-wrap: wrap; gap: 10px 16px; }
    .campos { gap: 10px; }
    .campos:disabled textarea { color: #ddd; border-color: #555; }
    /* Deshabilitados, los radios quedan grises: se resalta la opcion marcada para que se lea */
    .campos:disabled label { color: #777; }
    .campos:disabled label:has(input:checked) { color: #fff; font-weight: 700; }
    .campos:disabled label:has(input:checked)::after { content: ' ✓'; color: #76c410; }
    legend { padding: 0; margin-bottom: 4px; font-size: 13px; color: #ccc; }
    textarea { width: 100%; resize: vertical; padding: 8px; font: inherit; background: #222; color: #fff; border: 1px solid #777; }
    button { align-self: flex-end; padding: 8px 16px; font: inherit; border: 2px solid #1e6fff; background: #222; color: #fff; cursor: pointer; }
    button:disabled { opacity: 0.4; cursor: not-allowed; }
    .aviso { margin: 0; font-size: 13px; }
    .aviso.error { color: #ff7a7a; }
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
