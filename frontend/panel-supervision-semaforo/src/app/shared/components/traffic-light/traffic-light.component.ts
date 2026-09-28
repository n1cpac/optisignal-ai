import { Component, Input } from '@angular/core';

import { EstadoSemaforo } from '../../../core/models/status.model';

@Component({
  selector: 'app-traffic-light',
  standalone: true,
  template: `
    <div class="traffic-light" role="img" [attr.aria-label]="'Semáforo en ' + (estado ?? 'estado desconocido')">
      <span class="luz rojo" [class.activo]="estado === 'rojo'"></span>
      <span class="luz amarillo" [class.activo]="estado === 'amarillo'"></span>
      <span class="luz verde" [class.activo]="estado === 'verde'"></span>
    </div>
  `,
  styles: [`
    .traffic-light {
      display: inline-flex;
      flex-direction: column;
      gap: var(--spacing-12);
      padding: var(--spacing-16);
      background: var(--color-carbon);
      border: 1px solid var(--color-sky-paper);
      border-radius: var(--radius-controls);
    }

    .luz {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      opacity: 0.2;
      transition: opacity 160ms;
    }

    .rojo { background: var(--signal-red); }
    .amarillo { background: var(--signal-amber); }
    .verde { background: var(--signal-green); }

    /* Luz encendida: sin resplandor (nada de sombras); un aro blanco la marca */
    .luz.activo { opacity: 1; outline: 2px solid var(--color-paper-white); outline-offset: 3px; }

    @media (max-width: 640px) {
      .traffic-light { flex-direction: row; justify-content: center; justify-self: center; }
    }
  `]
})
export class TrafficLightComponent {
  @Input() estado: EstadoSemaforo | null = null;
}
