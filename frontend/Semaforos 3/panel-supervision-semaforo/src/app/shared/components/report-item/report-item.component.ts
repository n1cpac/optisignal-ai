import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DatePipe } from '@angular/common';

import { Reporte } from '../../../core/models/reporte.model';

@Component({
  selector: 'app-report-item',
  standalone: true,
  imports: [DatePipe],
  template: `
    <button type="button" class="item" [class.activo]="seleccionado" (click)="seleccionar.emit()">
      <span class="ubicacion">{{ reporte.ubicacion }}</span>
      <span class="fecha">{{ reporte.fecha | date: 'dd/MM/yyyy HH:mm' }}</span>
      <span class="descripcion">{{ reporte.descripcion }}</span>
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
    .ubicacion { font-weight: 600; }
    .fecha { font-size: 12px; color: #aaa; }
    .descripcion { font-size: 13px; }
  `]
})
export class ReportItemComponent {
  @Input({ required: true }) reporte!: Reporte;
  @Input() seleccionado = false;
  @Output() seleccionar = new EventEmitter<void>();
}
