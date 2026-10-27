import { Component, Input, OnChanges, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { Destinatario } from '../../core/models/reporte.model';

type EstadoEnvio = 'inactivo' | 'enviando' | 'enviado' | 'error';

@Component({
  selector: 'app-report-form',
  standalone: true,
  imports: [FormsModule],
  template: `
    <form class="reporte" (ngSubmit)="enviar()">
      <h3>Reporte</h3>

      <fieldset>
        <legend>La detección eléctrica, ¿coincide con la imagen?</legend>
        <label><input type="radio" name="coincide" [value]="true" [(ngModel)]="coincide" /> Coincide</label>
        <label><input type="radio" name="coincide" [value]="false" [(ngModel)]="coincide" /> No coincide</label>
      </fieldset>

      <textarea
        name="comentario"
        rows="4"
        placeholder="Escribe el reporte..."
        [(ngModel)]="comentario"
      ></textarea>

      <fieldset>
        <legend>Enviar a</legend>
        <label><input type="checkbox" name="transito" [(ngModel)]="destinatarios.transito" /> Policía de tránsito</label>
        <label><input type="checkbox" name="tecnicos" [(ngModel)]="destinatarios.tecnicos" /> Técnicos de reparación</label>
      </fieldset>

      <button type="submit" [disabled]="!puedeEnviar">Enviar ▶</button>

      @if (estado === 'enviando') { <p class="aviso">Enviando...</p> }
      @if (estado === 'enviado') { <p class="aviso">Reporte enviado.</p> }
      @if (estado === 'error') { <p class="aviso error">No se pudo enviar. Intenta de nuevo.</p> }
    </form>
  `,
  styles: [`
    .reporte { display: flex; flex-direction: column; gap: 10px; border: 2px solid #fff; padding: 12px; }
    h3 { margin: 0; font-size: 20px; }
    fieldset { border: 0; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
    legend { padding: 0; margin-bottom: 4px; font-size: 13px; color: #ccc; }
    textarea { width: 100%; resize: vertical; padding: 8px; font: inherit; background: #222; color: #fff; border: 1px solid #777; }
    button { align-self: flex-end; padding: 8px 16px; font: inherit; border: 2px solid #1e6fff; background: #222; color: #fff; cursor: pointer; }
    button:disabled { opacity: 0.4; cursor: not-allowed; }
    .aviso { margin: 0; font-size: 13px; }
    .aviso.error { color: #ff7a7a; }
  `]
})
export class ReportFormComponent implements OnChanges {
  /** Al cambiar de semaforo el formulario se limpia. */
  @Input({ required: true }) semaforoId!: string;

  private api = inject(ApiService);

  coincide: boolean | null = null;
  comentario = '';
  destinatarios = { transito: true, tecnicos: false };
  estado: EstadoEnvio = 'inactivo';

  get puedeEnviar(): boolean {
    return (
      this.coincide !== null &&
      (this.destinatarios.transito || this.destinatarios.tecnicos) &&
      this.estado !== 'enviando'
    );
  }

  ngOnChanges(): void {
    this.reiniciar();
    this.estado = 'inactivo';
  }

  enviar(): void {
    if (!this.puedeEnviar || this.coincide === null) return;

    const destinatarios: Destinatario[] = [];
    if (this.destinatarios.transito) destinatarios.push('transito');
    if (this.destinatarios.tecnicos) destinatarios.push('tecnicos');

    this.estado = 'enviando';
    this.api
      .enviarReporte({
        semaforoId: this.semaforoId,
        coincide: this.coincide,
        comentario: this.comentario.trim(),
        destinatarios
      })
      .subscribe({
        next: () => {
          this.reiniciar();
          this.estado = 'enviado';
        },
        error: () => (this.estado = 'error')
      });
  }

  private reiniciar(): void {
    this.coincide = null;
    this.comentario = '';
    this.destinatarios = { transito: true, tecnicos: false };
  }
}
