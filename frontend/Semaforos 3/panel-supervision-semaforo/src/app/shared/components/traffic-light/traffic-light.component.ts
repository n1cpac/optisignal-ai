import { Component, Input, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';

import { EstadoLuz } from '../../../core/models/semaforo.model';

/** Secuencia normal (normativa colombiana): rojo, amarillo, verde, amarillo. */
const CICLO: EstadoLuz[] = ['rojo', 'amarillo', 'verde', 'amarillo'];
const CICLO_MS = 2500;

@Component({
  selector: 'app-traffic-light',
  standalone: true,
  template: `
    <div class="semaforo" role="img" [attr.aria-label]="'Luz encendida: ' + (encendidas.join(' y ') || 'ninguna')">
      <span class="luz rojo" [class.activo]="encendidas.includes('rojo')" [class.parpadeo]="parpadeo === 'rojo'"></span>
      <span class="luz amarillo" [class.activo]="encendidas.includes('amarillo')" [class.parpadeo]="parpadeo === 'amarillo'"></span>
      <span class="luz verde" [class.activo]="encendidas.includes('verde')" [class.parpadeo]="parpadeo === 'verde'"></span>
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
    .luz.parpadeo { animation: parpadeo 1s steps(1) infinite; }
    .rojo.parpadeo { --c: #ff4a1c; }
    .amarillo.parpadeo { --c: #ffe000; }
    .verde.parpadeo { --c: #76c410; }
    @keyframes parpadeo { 0% { background: var(--c); } 50% { background: transparent; } }
  `]
})
export class TrafficLightComponent implements OnChanges, OnDestroy {
  /** Luces encendidas fijas; puede haber varias a la vez (una falla). */
  @Input() luces: EstadoLuz[] = [];
  /** Luz que parpadea (falla de amarillo intermitente). */
  @Input() parpadeo: EstadoLuz | null = null;
  /** Recorre rojo, amarillo y verde como un semaforo funcional; ignora `luces`. */
  @Input() ciclo = false;

  private fase = 0;
  private timer?: ReturnType<typeof setInterval>;

  get encendidas(): EstadoLuz[] {
    if (this.ciclo) return [CICLO[this.fase]];
    return this.parpadeo ? [this.parpadeo] : this.luces;
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Solo reacciona a `ciclo`: `luces` llega como arreglo nuevo en cada actualizacion del panel
    if (!changes['ciclo']) return;
    this.detener();
    if (this.ciclo) {
      this.fase = 0;
      this.timer = setInterval(() => (this.fase = (this.fase + 1) % CICLO.length), CICLO_MS);
    }
  }

  ngOnDestroy(): void {
    this.detener();
  }

  private detener(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }
}
