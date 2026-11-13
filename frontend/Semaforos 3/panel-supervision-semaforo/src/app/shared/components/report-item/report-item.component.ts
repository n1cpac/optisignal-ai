import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DatePipe } from '@angular/common';

import { Reporte } from '../../../core/models/reporte.model';
import { ZONA_BOGOTA } from '../../hora-bogota';

const NOMBRES_ANOMALIA: Record<string, string> = {
  ELECTRICAL_FAULT: 'Falla en el sistema eléctrico',
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
      <span class="icono" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 3.5l9.5 16.5h-19z" /><path d="M12 10v4.5M12 17.2v.1" /></svg>
      </span>
      <span class="contenido">
        @if (nueva) {
          <span class="etiqueta-nueva">● Nueva alerta</span>
        }
        <span class="fila">
          <span class="ubicacion">{{ reporte.ubicacion }}</span>
          <span class="hora">{{ reporte.fecha | date: 'HH:mm' : zona }}</span>
        </span>
        <span class="fecha">{{ reporte.fecha | date: 'dd/MM/yyyy' : zona }}</span>
        <span class="chip">{{ nombreAlerta }}</span>
      </span>
    </button>
  `,
  styles: [`
    :host { display: block; margin-bottom: var(--sp-2); }
    .item {
      display: flex;
      align-items: flex-start;
      gap: var(--sp-3);
      width: 100%;
      padding: var(--sp-3);
      border: 1px solid transparent;
      border-radius: var(--r-control);
      background: transparent;
      color: var(--text);
      text-align: left;
      font: inherit;
      cursor: pointer;
    }
    .item:hover { background: color-mix(in srgb, var(--border) 50%, transparent); }
    .item.activo { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); }
    .item.nueva { border-color: var(--warning); animation: destello 1.2s ease-in-out 3; }
    @keyframes destello { 50% { background: color-mix(in srgb, var(--warning) 18%, transparent); } }
    @media (prefers-reduced-motion: reduce) { .item.nueva { animation: none; background: color-mix(in srgb, var(--warning) 12%, transparent); } }
    .icono {
      display: inline-flex;
      flex: none;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: var(--r-control);
      background: color-mix(in srgb, var(--danger) 12%, transparent);
    }
    .icono path { fill: none; stroke: var(--danger); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
    .contenido { display: flex; flex: 1; flex-direction: column; gap: 3px; min-width: 0; }
    .fila { display: flex; justify-content: space-between; align-items: baseline; gap: var(--sp-2); }
    .ubicacion { font-weight: 600; font-size: 14px; }
    .hora { flex: none; font-family: var(--font-mono); font-size: 12px; color: var(--text); }
    .fecha { font-size: 12px; color: var(--text-muted); }
    .chip {
      align-self: flex-start;
      padding: 2px 8px;
      border-radius: var(--r-chip);
      background: var(--chip-bg);
      color: var(--warning);
      font-size: 12px;
      font-weight: 500;
    }
    .etiqueta-nueva { color: var(--warning); font-size: 12px; font-weight: 600; }
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

  protected readonly zona = ZONA_BOGOTA;

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
