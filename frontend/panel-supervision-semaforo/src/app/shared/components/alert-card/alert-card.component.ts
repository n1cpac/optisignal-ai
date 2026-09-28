import { Component, EventEmitter, Input, Output } from '@angular/core';
import { DatePipe } from '@angular/common';

import { AlertRecord } from '../../../core/models/alert.model';

/** Una alerta como fila del libro de registro (usa .fila-alerta de styles.css). */
@Component({
  selector: 'app-alert-card',
  standalone: true,
  imports: [DatePipe],
  template: `
    <div class="fila-alerta">
      <div class="detalle">
        <p class="tipo">{{ alerta?.tipoFalla }}</p>
        @if (alerta?.descripcion) {
          <p class="texto-secundario">{{ alerta?.descripcion }}</p>
        }
      </div>
      <p class="etiqueta">{{ alerta?.fecha | date: 'dd/MM/yyyy HH:mm' }}</p>
      <button type="button" class="btn btn--sm" (click)="verEvidencia.emit(alerta!)">Ver evidencia</button>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .tipo { font-size: 18px; font-weight: 500; letter-spacing: -0.01em; }
    .detalle { min-width: 0; }
    .detalle .texto-secundario { margin-top: var(--spacing-4); font-size: 15px; }
    /* Etiqueta mono de la fecha en tinta negra: es un dato, no un rótulo */
    .etiqueta { color: var(--color-ink-black); }
  `]
})
export class AlertCardComponent {
  @Input() alerta: AlertRecord | null = null;
  @Output() verEvidencia = new EventEmitter<AlertRecord>();
}
