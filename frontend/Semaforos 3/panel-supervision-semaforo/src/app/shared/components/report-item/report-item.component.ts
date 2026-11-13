import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DatePipe } from '@angular/common';

import { Reporte } from '../../../core/models/reporte.model';

const NOMBRES_ANOMALIA: Record<string, string> = {
  AMARILLO_INTERMITENTE: 'Amarillo intermitente en falla',
  ALL_LIGHTS_OFF: 'Semáforo apagado (sin luces)',
  MULTIPLE_LIGHTS_ON: 'Múltiples luces encendidas',
  LIGHT_STUCK: 'Luz estancada en una fase',
  INVALID_TRANSITION: 'Secuencia de luces inválida',
  LOW_BRIGHTNESS: 'Baja intensidad luminosa',
  OBSTRUCTED_LIGHT: 'Lente obstruido'
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
      <span class="nombre-alerta">{{ nombreAlerta }}</span>
    </button>
  `,
  styles: [`
    .item {
      display: flex;
      flex-direction: column;
      gap: 3px;
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
    .ubicacion { font-weight: 600; font-size: 14px; }
    .fecha { font-size: 12px; color: #aaa; }
    .nombre-alerta { font-size: 13px; color: #e2e8f0; }
  `]
})
export class ReportItemComponent {
  @Input({ required: true }) reporte!: Reporte;
  @Input() seleccionado = false;
  /** Conservado por compatibilidad con el contenedor; el resumen izquierdo siempre se muestra simplificado. */
  @Input() detalle = false;
  /** Llego una alerta nueva de este semaforo y aun no se abre: se resalta y sube al principio. */
  @Input() nueva = false;
  @Output() seleccionar = new EventEmitter<void>();

  protected get nombreAlerta(): string {
    const desc = this.reporte.descripcion ?? '';
    for (const [codigo, nombre] of Object.entries(NOMBRES_ANOMALIA)) {
      if (desc.includes(codigo)) {
        return nombre;
      }
    }

    if (!this.reporte.automatica && this.reporte.opciones) {
      const o = this.reporte.opciones;
      if (o.falla) {
        const base =
          o.tipoFalla === 'dano'
            ? 'Falla por daño'
            : o.tipoFalla === 'funcionamiento'
              ? 'Falla por funcionamiento'
              : 'Falla en semáforo';
        if (o.semaforosAfectados?.length) {
          return `${base} · Semáforo #${o.semaforosAfectados.join(', #')}`;
        }
        return base;
      }
      if (o.falla === false) {
        return 'Funcionamiento normal (sin fallo)';
      }
    }

    return desc
      .replace(/^\[Alerta Automatica Vision\]\s*/i, '')
      .replace(/^Falla:\s*/i, '')
      .split('.')[0]
      .trim() || 'Alerta de semáforo';
  }
}
