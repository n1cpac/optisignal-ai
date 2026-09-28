import { AfterViewInit, Component, ElementRef, EventEmitter, HostListener, Input, Output, ViewChild } from '@angular/core';
import { DatePipe } from '@angular/common';

import { AlertRecord } from '../../../core/models/alert.model';

/** Modal con el fotograma de evidencia. Se cierra con el botón, con Esc o al pulsar el fondo. */
@Component({
  selector: 'app-evidence-modal',
  standalone: true,
  imports: [DatePipe],
  template: `
    <div class="fondo" (click)="cerrar.emit()">
      <div class="modal" role="dialog" aria-modal="true" [attr.aria-label]="'Evidencia: ' + alerta.tipoFalla"
           (click)="$event.stopPropagation()">
        <div class="modal__cabecera">
          <div>
            <h2 class="modal__titulo">{{ alerta.tipoFalla }}</h2>
            <p class="etiqueta">{{ alerta.fecha | date: 'dd/MM/yyyy HH:mm' }}</p>
          </div>
          <button #cerrarBtn type="button" class="btn btn--sm" (click)="cerrar.emit()">Cerrar</button>
        </div>

        @if (alerta.fotogramaUrl) {
          <img class="modal__imagen" [src]="alerta.fotogramaUrl" [alt]="'Fotograma de la alerta: ' + alerta.tipoFalla" />
        } @else {
          <p class="modal__sin-imagen texto-secundario">Esta alerta no tiene fotograma asociado.</p>
        }

        @if (alerta.descripcion) {
          <p class="modal__descripcion">{{ alerta.descripcion }}</p>
        }
      </div>
    </div>
  `,
  styles: [`
    .fondo {
      position: fixed;
      inset: 0;
      z-index: 3000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-16);
      background: rgba(9, 35, 79, 0.88);
    }

    .modal {
      width: min(720px, 100%);
      max-height: 100%;
      overflow-y: auto;
      background: var(--color-paper-white);
      border: 1px solid var(--color-steel-rule);
    }

    .modal__cabecera {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--spacing-16);
      padding: var(--card-padding);
      border-bottom: 1px solid var(--color-rule-gray);
    }

    .modal__titulo {
      margin-bottom: var(--spacing-4);
      font-size: 24px;
      font-weight: 500;
      line-height: 1.35;
      letter-spacing: -0.24px;
    }

    .modal__imagen { width: 100%; aspect-ratio: 3 / 2; object-fit: cover; background: var(--color-mint-paper); }
    .modal__sin-imagen { padding: var(--spacing-48) var(--card-padding); text-align: center; background: var(--color-mint-paper); }
    .modal__descripcion { padding: var(--card-padding); border-top: 1px solid var(--color-rule-gray); }
  `]
})
export class EvidenceModalComponent implements AfterViewInit {
  @Input({ required: true }) alerta!: AlertRecord;
  @Output() cerrar = new EventEmitter<void>();

  @ViewChild('cerrarBtn') private cerrarBtn?: ElementRef<HTMLButtonElement>;

  ngAfterViewInit(): void {
    this.cerrarBtn?.nativeElement.focus(); // el foco entra al diálogo
  }

  @HostListener('document:keydown.escape')
  alPulsarEscape(): void {
    this.cerrar.emit();
  }
}
