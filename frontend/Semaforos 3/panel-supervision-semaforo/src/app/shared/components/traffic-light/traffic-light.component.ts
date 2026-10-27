import { Component, Input } from '@angular/core';

import { EstadoLuz } from '../../../core/models/semaforo.model';

@Component({
  selector: 'app-traffic-light',
  standalone: true,
  template: `
    <div class="semaforo" role="img" [attr.aria-label]="'Luz encendida: ' + (estado ?? 'sin dato')">
      <span class="luz rojo" [class.activo]="estado === 'rojo'"></span>
      <span class="luz amarillo" [class.activo]="estado === 'amarillo'"></span>
      <span class="luz verde" [class.activo]="estado === 'verde'"></span>
    </div>
  `,
  styles: [`
    .semaforo {
      display: inline-flex;
      flex-direction: column;
      gap: 12px;
      padding: 12px 16px;
      border: 3px solid #fff;
      background: #222;
    }
    .luz {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: 4px solid;
    }
    .rojo { border-color: #ff4a1c; }
    .amarillo { border-color: #ffe000; }
    .verde { border-color: #76c410; }
    .rojo.activo { background: #ff4a1c; }
    .amarillo.activo { background: #ffe000; }
    .verde.activo { background: #76c410; }
  `]
})
export class TrafficLightComponent {
  @Input() estado: EstadoLuz | null = null;
}
