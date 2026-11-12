import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  computed,
  inject,
  signal
} from '@angular/core';

import { PanelStateService } from './core/services/panel-state.service';
import { ReportHistoryComponent } from './features/report-history/report-history.component';
import { CityMapComponent } from './features/city-map/city-map.component';
import { SemaforoDetailComponent } from './features/semaforo-detail/semaforo-detail.component';

type Lado = 'izq' | 'der';

/** Limites al arrastrar: el mapa conserva al menos el 20% del ancho. */
const LIMITES: Record<Lado, { min: number; maxFraccion: number }> = {
  izq: { min: 180, maxFraccion: 0.3 },
  der: { min: 260, maxFraccion: 0.5 }
};
/** Sin arrastrar, los paneles siguen el tamano de la ventana. */
const POR_DEFECTO: Record<Lado, string> = {
  izq: 'clamp(200px, 18vw, 320px)',
  der: 'clamp(280px, 24vw, 460px)'
};
const PASO_TECLADO = 24;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ReportHistoryComponent, CityMapComponent, SemaforoDetailComponent],
  template: `
    <div class="app">
      <header class="encabezado">OPTISIGNAL</header>

      <div
        #cuerpo
        class="cuerpo"
        [class.arrastrando]="arrastrando() !== null"
        [style.--col-izq]="columna('izq')"
        [style.--col-der]="columna('der')"
      >
        <aside #izq class="izquierda"><app-report-history /></aside>
        <div
          class="separador"
          role="separator"
          tabindex="0"
          aria-orientation="vertical"
          aria-label="Ancho del panel de reportes. Flechas para cambiarlo, doble clic para restablecerlo."
          [attr.aria-valuenow]="anchos().izq"
          [attr.aria-valuemin]="limites.izq.min"
          [attr.aria-valuemax]="maximo('izq')"
          (pointerdown)="iniciar('izq', $event)"
          (pointermove)="mover($event)"
          (pointerup)="soltar()"
          (pointercancel)="soltar()"
          (dblclick)="restablecer('izq')"
          (keydown)="teclado('izq', $event)"
        ></div>
        <main class="centro"><app-city-map /></main>
        <div
          class="separador"
          role="separator"
          tabindex="0"
          aria-orientation="vertical"
          aria-label="Ancho del panel de detalle. Flechas para cambiarlo, doble clic para restablecerlo."
          [attr.aria-valuenow]="anchos().der"
          [attr.aria-valuemin]="limites.der.min"
          [attr.aria-valuemax]="maximo('der')"
          (pointerdown)="iniciar('der', $event)"
          (pointermove)="mover($event)"
          (pointerup)="soltar()"
          (pointercancel)="soltar()"
          (dblclick)="restablecer('der')"
          (keydown)="teclado('der', $event)"
        ></div>
        <aside #der class="derecha"><app-semaforo-detail /></aside>
      </div>
    </div>
  `,
  styles: [`
    .app { display: grid; grid-template-rows: auto 1fr; height: 100%; }
    .encabezado {
      background: #0047a8;
      color: #fff;
      padding: 14px 24px;
      font-size: 30px;
      letter-spacing: 0.25em;
    }
    .cuerpo {
      display: grid;
      grid-template-columns: var(--col-izq) 6px minmax(0, 1fr) 6px var(--col-der);
      min-height: 0;
    }
    .cuerpo.arrastrando { cursor: col-resize; user-select: none; }
    .izquierda, .derecha { background: #222; color: #fff; overflow-y: auto; min-width: 0; }
    .derecha { padding: 16px; }
    .centro { position: relative; min-width: 0; background: #fff; }
    .separador { background: #333; cursor: col-resize; touch-action: none; }
    .separador:hover, .separador:focus-visible { background: #1e6fff; outline: none; }
    .arrastrando .separador:active { background: #1e6fff; }

    /* Pantallas angostas: una sola columna, con el mapa arriba */
    @media (max-width: 900px) {
      .app { height: auto; min-height: 100%; }
      .encabezado { padding: 10px 16px; font-size: 22px; }
      .cuerpo {
        grid-template-columns: 1fr;
        grid-template-areas: 'centro' 'derecha' 'izquierda';
      }
      .centro { grid-area: centro; height: 60vh; }
      .derecha { grid-area: derecha; }
      .izquierda { grid-area: izquierda; }
      .izquierda, .derecha { overflow-y: visible; }
      .separador { display: none; }
    }
  `]
})
export class AppComponent implements AfterViewInit, OnDestroy {
  protected state = inject(PanelStateService);
  protected readonly limites = LIMITES;

  @ViewChild('cuerpo', { static: true }) private cuerpo!: ElementRef<HTMLElement>;
  @ViewChild('izq', { static: true }) private izq!: ElementRef<HTMLElement>;
  @ViewChild('der', { static: true }) private der!: ElementRef<HTMLElement>;

  /** Ancho elegido al arrastrar, en px; null sigue el tamano de la ventana. */
  private anchoElegido = signal<Record<Lado, number | null>>({ izq: null, der: null });
  /** Ancho real en pantalla (para lectores de pantalla y para mover con el teclado). */
  protected anchos = signal<Record<Lado, number>>({ izq: 0, der: 0 });
  protected arrastrando = signal<Lado | null>(null);
  private observador?: ResizeObserver;

  /** Valor de cada columna; la camara expandida ocupa media pantalla. */
  protected columna = (lado: Lado): string => {
    if (lado === 'der' && this.state.camaraExpandida()) return '50%';
    const elegido = this.anchoElegido()[lado];
    if (elegido === null) return POR_DEFECTO[lado];
    // Si la ventana se achica, el panel se achica con ella en lugar de tapar el mapa
    return `min(${elegido}px, ${LIMITES[lado].maxFraccion * 100}vw)`;
  };

  protected maximo = (lado: Lado): number =>
    Math.round(this.anchoCuerpo() * LIMITES[lado].maxFraccion);

  private anchoCuerpo = signal(0);

  ngAfterViewInit(): void {
    this.observador = new ResizeObserver(() => {
      this.anchos.set({ izq: this.izq.nativeElement.offsetWidth, der: this.der.nativeElement.offsetWidth });
      this.anchoCuerpo.set(this.cuerpo.nativeElement.offsetWidth);
    });
    for (const el of [this.cuerpo, this.izq, this.der]) this.observador.observe(el.nativeElement);
  }

  ngOnDestroy(): void {
    this.observador?.disconnect();
  }

  protected iniciar(lado: Lado, evento: PointerEvent): void {
    if (evento.button !== 0) return;
    // La captura hace que el separador siga recibiendo el movimiento aunque el puntero salga de el
    (evento.target as HTMLElement).setPointerCapture(evento.pointerId);
    this.arrastrando.set(lado);
  }

  protected mover(evento: PointerEvent): void {
    const lado = this.arrastrando();
    if (!lado) return;
    const caja = this.cuerpo.nativeElement.getBoundingClientRect();
    this.fijar(lado, lado === 'izq' ? evento.clientX - caja.left : caja.right - evento.clientX);
  }

  protected soltar(): void {
    this.arrastrando.set(null);
  }

  protected restablecer(lado: Lado): void {
    this.anchoElegido.update((actual) => ({ ...actual, [lado]: null }));
  }

  /** Flechas: mueven el separador en la direccion de la flecha. */
  protected teclado(lado: Lado, evento: KeyboardEvent): void {
    const direccion = { ArrowLeft: -1, ArrowRight: 1 }[evento.key];
    if (!direccion) return;
    evento.preventDefault();
    const crece = lado === 'izq' ? direccion : -direccion;
    // Ancho real del momento: la senal `anchos` se actualiza despues y quedaria atrasada si se pulsa rapido
    const panel = (lado === 'izq' ? this.izq : this.der).nativeElement;
    this.fijar(lado, panel.offsetWidth + crece * PASO_TECLADO);
  }

  private fijar(lado: Lado, ancho: number): void {
    const { min, maxFraccion } = LIMITES[lado];
    const maximo = this.cuerpo.nativeElement.offsetWidth * maxFraccion;
    const limitado = Math.round(Math.min(Math.max(ancho, min), maximo));
    // Arrastrar el panel derecho deja el modo expandido para respetar el ancho elegido
    if (lado === 'der' && this.state.camaraExpandida()) this.state.camaraExpandida.set(false);
    this.anchoElegido.update((actual) => ({ ...actual, [lado]: limitado }));
  }
}
