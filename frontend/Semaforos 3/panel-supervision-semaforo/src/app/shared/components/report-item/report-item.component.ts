import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DatePipe } from '@angular/common';

import { Destinatario, Reporte } from '../../../core/models/reporte.model';

const NOMBRES_DESTINATARIO: Record<Destinatario, string> = {
  transito: 'Policía de tránsito',
  tecnicos: 'Técnicos de reparación'
};

@Component({
  selector: 'app-report-item',
  standalone: true,
  imports: [DatePipe],
  template: `
    <button type="button" class="item" [class.activo]="seleccionado" [class.nueva]="nueva" (click)="seleccionar.emit()">
      @if (nueva) {
        <span class="etiqueta-nueva">● Nueva alerta</span>
      }
      <span class="ubicacion">{{ reporte.ubicacion }}</span>
      <span class="fecha">{{ reporte.fecha | date: 'dd/MM/yyyy HH:mm' }}</span>
      <span class="descripcion">{{ reporte.descripcion }}</span>

      @if (detalle) {
        <span class="estado" [class]="'estado ' + estado.clase">{{ estado.texto }}</span>
        @if (reporte.opciones; as o) {
          @if (reporte.alertasVerificadas) {
            <span class="dato">
              Verificó {{ reporte.alertasVerificadas }} {{ reporte.alertasVerificadas === 1 ? 'alerta' : 'alertas' }}
            </span>
          }
          <span class="dato">
            {{ o.coincide ? 'Coincide' : 'No coincide' }} ·
            {{ o.falla === null ? 'Fallo sin registrar' : o.falla ? 'Fallo en el semáforo' : 'Sin fallo' }}
          </span>
          @if (o.falla) {
            <span class="dato">Enviado a: {{ destinatarios(o.destinatarios) }}</span>
          }
          @if (o.comentario) {
            <span class="comentario">“{{ o.comentario }}”</span>
          }
        }
      }
    </button>
  `,
  styles: [`
    .item {
      display: flex;
      flex-direction: column;
      gap: 2px;
      width: 100%;
      padding: 10px 12px;
      border: 0;
      border-left: 4px solid transparent;
      border-bottom: 1px solid #444;
      background: transparent;
      color: #fff;
      text-align: left;
      font: inherit;
      cursor: pointer;
    }
    .item:hover { background: #2f2f2f; }
    .item.activo { background: #1d3a6e; border-left-color: #1e6fff; }
    .item.nueva { border-left-color: #ffd54f; animation: destello 1.2s ease-in-out 3; }
    @keyframes destello { 50% { background: #5a4a12; } }
    @media (prefers-reduced-motion: reduce) { .item.nueva { animation: none; background: #3d3412; } }
    .etiqueta-nueva { color: #ffd54f; font-size: 12px; font-weight: 700; }
    .ubicacion { font-weight: 600; }
    .fecha { font-size: 12px; color: #aaa; }
    .descripcion { font-size: 13px; }
    .estado { align-self: flex-start; margin-top: 4px; padding: 1px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; }
    .estado.atendido { background: #2e5e12; }
    .estado.pendiente { background: #8a1f1c; }
    .dato { font-size: 12px; color: #ccc; }
    .comentario { font-size: 12px; font-style: italic; color: #ddd; }
  `]
})
export class ReportItemComponent {
  @Input({ required: true }) reporte!: Reporte;
  @Input() seleccionado = false;
  /** Muestra si fue atendido y las opciones y el comentario del reporte (pestana de historial). */
  @Input() detalle = false;
  /** Llego una alerta nueva de este semaforo y aun no se abre: se resalta y sube al principio. */
  @Input() nueva = false;
  @Output() seleccionar = new EventEmitter<void>();

  /** Verificado: el operario lo confirmo con un reporte (una alerta atendida o un reporte propio). */
  protected get estado(): { texto: string; clase: string } {
    return this.reporte.opciones
      ? { texto: 'Reporte verificado', clase: 'atendido' }
      : { texto: 'No verificado', clase: 'pendiente' };
  }

  protected destinatarios(lista: Destinatario[]): string {
    return lista.length ? lista.map((d) => NOMBRES_DESTINATARIO[d]).join(', ') : 'nadie';
  }
}
