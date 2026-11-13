import { Component, Input, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';

import { EstadoLuz } from '../../../core/models/semaforo.model';

/** Secuencia normal (normativa colombiana): rojo, amarillo, verde, amarillo. */
const CICLO: EstadoLuz[] = ['rojo', 'amarillo', 'verde', 'amarillo'];
const CICLO_MS = 2500;

@Component({
  selector: 'app-traffic-light',
  standalone: true,
  template: `
    <div class="semaforo" role="img" [attr.aria-label]="'Luz encendida: ' + (encendidas.join(' y ') || 'ninguna') + (parpadeo ? ' (parpadeando)' : '')">
      <span class="luz rojo" [class.activo]="encendidas.includes('rojo')" [class.parpadeo]="parpadeo === 'rojo'"></span>
      <span class="luz amarillo" [class.activo]="encendidas.includes('amarillo')" [class.parpadeo]="parpadeo === 'amarillo'"></span>
      <span class="luz verde" [class.activo]="encendidas.includes('verde')" [class.parpadeo]="parpadeo === 'verde'"></span>
    </div>
  `,
  styles: [`
    /* Carcasa de 72px con tres luces de 44px; la apagada es un tono muy oscuro de su color */
    .semaforo {
      display: inline-flex;
      flex-direction: column;
      gap: 10px;
      width: 72px;
      padding: 14px;
      background: var(--surface-deep);
      border: 1px solid var(--border);
      border-radius: var(--r-shell);
    }
    .luz {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: color-mix(in srgb, var(--c) 18%, var(--surface-deep));
    }
    .rojo { --c: var(--danger); }
    .amarillo { --c: var(--warning); }
    .verde { --c: var(--ok); }
    .luz.activo { background: var(--c); box-shadow: 0 0 18px color-mix(in srgb, var(--c) 70%, transparent); }
    .luz.parpadeo { animation: parpadeo 1s steps(1) infinite; }
    @keyframes parpadeo {
      0% { background: var(--c); box-shadow: 0 0 18px color-mix(in srgb, var(--c) 70%, transparent); }
      50% { background: color-mix(in srgb, var(--c) 18%, var(--surface-deep)); box-shadow: none; }
    }
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
