import { Component, EventEmitter, Input, OnChanges, Output, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { Destinatario, OpcionesReporte } from '../../core/models/reporte.model';

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
  /** Opciones de un reporte ya verificado: el formulario las muestra en solo lectura. */
  @Input() opciones: OpcionesReporte | null = null;
  /** Id del reporte recien creado. */
  @Output() enviado = new EventEmitter<string>();

  private api = inject(ApiService);

  coincide: boolean | null = null;
  falla: boolean | null = null;
  comentario = '';
  destinatarios = { transito: false, tecnicos: false };
  estado: EstadoEnvio = 'inactivo';

  get puedeEnviar(): boolean {
    return this.coincide !== null && this.falla !== null && this.estado !== 'enviando';
  }

  ngOnChanges(): void {
    this.estado = 'inactivo';
    if (!this.opciones) {
      this.reiniciar();
      return;
    }
    this.coincide = this.opciones.coincide;
    this.falla = this.opciones.falla;
    this.comentario = this.opciones.comentario ?? '';
    this.destinatarios = {
      transito: this.opciones.destinatarios.includes('transito'),
      tecnicos: this.opciones.destinatarios.includes('tecnicos')
    };
  }

  enviar(): void {
    if (!this.puedeEnviar || this.coincide === null || this.falla === null) return;

    // Los destinatarios solo cuentan con fallo: si se marcaron y luego se eligio "No hay fallo", no se envian
    const destinatarios: Destinatario[] = [];
    if (this.falla && this.destinatarios.transito) destinatarios.push('transito');
    if (this.falla && this.destinatarios.tecnicos) destinatarios.push('tecnicos');

    this.estado = 'enviando';
    this.api
      .enviarReporte({
        semaforoId: this.semaforoId,
        coincide: this.coincide,
        falla: this.falla,
        comentario: this.comentario.trim(),
        destinatarios
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
    this.comentario = '';
    this.destinatarios = { transito: false, tecnicos: false };
  }
}
