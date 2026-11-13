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
import { horaBogota } from './shared/hora-bogota';

type Lado = 'izq' | 'der';

/** Limites al arrastrar: el mapa conserva al menos el 20% del ancho. */
const LIMITES: Record<Lado, { min: number; maxFraccion: number }> = {
  izq: { min: 180, maxFraccion: 0.3 },
  der: { min: 260, maxFraccion: 0.5 }
};
/** Sin arrastrar, los paneles siguen el tamano de la ventana. */
const POR_DEFECTO: Record<Lado, string> = {
  izq: 'clamp(280px, 20.8vw, 320px)', // ~300px a 1440px
  der: 'clamp(360px, 26.4vw, 420px)' // ~380px a 1440px
};
const PASO_TECLADO = 24;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ReportHistoryComponent, CityMapComponent, SemaforoDetailComponent],
  template: `
    <div class="app">
      <header class="encabezado">
        <div class="marca">
          <svg class="icono-marca" viewBox="0 0 24 32" width="22" height="30" aria-hidden="true">
            <rect class="carcasa" x="3" y="1.5" width="18" height="29" rx="5" />
            <circle class="luz rojo" cx="12" cy="8.5" r="3" />
            <circle class="luz amarillo" cx="12" cy="16" r="3" />
            <circle class="luz verde" cx="12" cy="23.5" r="3" />
          </svg>
          <span class="nombre">OPTISIGNAL</span>
          <span class="subtitulo">Centro de control semafórico</span>
        </div>
        <div class="datos">
          <ul class="pildoras" aria-label="Resumen de semáforos">
            <li class="pildora"><i class="punto neutro"></i><span class="cifra">{{ state.resumen().total }}</span> monitoreados</li>
            <li class="pildora ok"><i class="punto"></i><span class="cifra">{{ state.resumen().activos }}</span> operando</li>
            <li class="pildora falla"><i class="punto"></i><span class="cifra">{{ state.resumen().conFallas }}</span> con falla</li>
          </ul>
          <div class="reloj">
            <span class="ciudad">BOGOTÁ D.C. ·</span>
            <time class="hora">{{ hora() }}</time>
            <span class="gmt">GMT-5</span>
          </div>
        </div>
      </header>

      <div
        #cuerpo
        class="cuerpo"
        [class.arrastrando]="arrastrando() !== null"
        [style.--col-izq]="columna('izq')"
        [style.--col-der]="columna('der')"
      >
        <aside #izq class="izquierda"><app-report-history /></aside>
        <div
          class="separador s1"
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
          class="separador s2"
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
      <button
        type="button"
        class="debug-reset"
        title="Reiniciar base de datos y alertas"
        aria-label="Reiniciar base de datos y alertas"
        (click)="state.resetearDemo()"
      ></button>
    </div>
  `,
  styles: [`
    .app { display: flex; flex-direction: column; min-height: 100%; }

    .encabezado {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--sp-2) var(--sp-4);
      min-height: 60px;
      padding: 0 var(--sp-5);
      background: var(--bg-header);
      border-bottom: 1px solid var(--border);
    }
    .marca { display: flex; align-items: center; gap: var(--sp-3); }
    .icono-marca .carcasa { fill: none; stroke: var(--accent); stroke-width: 1.5; }
    .icono-marca .rojo { fill: var(--danger); }
    .icono-marca .amarillo { fill: var(--warning); }
    .icono-marca .verde { fill: var(--ok); }
    .nombre { font-family: var(--font-display); font-weight: 700; font-size: 20px; letter-spacing: 0.24em; }
    .subtitulo {
      padding-left: var(--sp-3);
      border-left: 1px solid var(--border);
      color: var(--text-muted);
      font-size: 13px;
    }
    .datos { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2) var(--sp-4); }
    .pildoras { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin: 0; padding: 0; list-style: none; }
    .pildora {
      display: inline-flex;
      align-items: center;
      gap: var(--sp-2);
      padding: 6px 12px;
      border: 1px solid var(--border);
      border-radius: var(--r-pill);
      background: var(--surface);
      font-size: 13px;
      font-weight: 500;
    }
    .pildora .cifra { font-family: var(--font-mono); font-weight: 500; }
    .punto { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
    .punto.neutro { color: var(--text-muted); }
    .pildora.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 10%, transparent); border-color: color-mix(in srgb, var(--ok) 35%, transparent); }
    .pildora.falla { color: var(--danger); background: color-mix(in srgb, var(--danger) 12%, transparent); border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
    .pildora.ok .cifra, .pildora.falla .cifra { color: var(--text); }
    .reloj { display: flex; align-items: baseline; gap: var(--sp-2); font-family: var(--font-mono); }
    .ciudad { color: var(--text-muted); font-size: 12px; }
    .hora { color: var(--text); font-size: 15px; font-weight: 500; }
    .gmt { padding: 1px 6px; border: 1px solid var(--border); border-radius: var(--r-chip); color: var(--text-muted); font-size: 12px; }

    /* Tres zonas: el mapa absorbe el espacio sobrante. Los separadores de 12px son el hueco entre ellas. */
    .cuerpo {
      display: grid;
      grid-template-columns: var(--col-izq) var(--sp-3) minmax(0, 1fr) var(--sp-3) var(--col-der);
      grid-template-areas: 'izq s1 centro s2 der';
      height: calc(100vh - 60px);
      min-height: 544px;
      padding: var(--sp-3);
    }
    .cuerpo.arrastrando { cursor: col-resize; user-select: none; }
    .izquierda, .centro, .derecha { min-height: 0; min-width: 0; }
    .izquierda {
      grid-area: izq;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: var(--sp-3);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-panel);
    }
    .centro {
      grid-area: centro;
      position: relative;
      overflow: hidden;
      border: 1px solid var(--border);
      border-radius: var(--r-panel);
    }
    .derecha { grid-area: der; display: flex; flex-direction: column; gap: var(--sp-3); overflow-y: auto; }
    .separador { position: relative; cursor: col-resize; touch-action: none; }
    .separador.s1 { grid-area: s1; }
    .separador.s2 { grid-area: s2; }
    .separador::after {
      content: '';
      position: absolute;
      inset: 25% 5px;
      border-radius: var(--r-pill);
      background: transparent;
    }
    .separador:hover::after, .separador:focus-visible::after, .arrastrando .separador:active::after { background: var(--accent); }
    .separador:focus-visible { outline: none; }
    .debug-reset {
      position: fixed;
      left: 2px;
      bottom: 2px;
      width: 24px;
      height: 24px;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: transparent;
      cursor: pointer;
      z-index: 9999;
      opacity: 0;
      transition: opacity 0.2s, background 0.2s;
    }
    .debug-reset:hover, .debug-reset:focus-visible {
      opacity: 1;
      background: color-mix(in srgb, var(--danger) 45%, transparent);
    }

    /* Por debajo de ~1250px el detalle baja a una segunda fila */
    @media (max-width: 1250px) {
      .cuerpo {
        grid-template-columns: var(--col-izq) var(--sp-3) minmax(0, 1fr);
        grid-template-areas: 'izq s1 centro' 'der der der';
        grid-template-rows: calc(100vh - 84px) auto;
        row-gap: var(--sp-3);
        height: auto;
      }
      .izquierda, .centro { min-height: 520px; }
      .s2 { display: none; }
      .derecha { overflow-y: visible; }
    }

    /* Movil: lista, mapa y detalle apilados a ancho completo */
    @media (max-width: 900px) {
      .encabezado { padding: var(--sp-2) var(--sp-4); }
      .nombre { font-size: 18px; }
      .cuerpo {
        grid-template-columns: minmax(0, 1fr);
        grid-template-areas: 'izq' 'centro' 'der';
        grid-template-rows: none;
      }
      .izquierda { min-height: 0; max-height: 60vh; }
      .centro { min-height: 0; height: 60vh; }
      .separador { display: none; }
    }
  `]
})
export class AppComponent implements AfterViewInit, OnDestroy {
  protected state = inject(PanelStateService);
  protected hora = signal(horaBogota(Date.now()));
  private relojId = setInterval(() => this.hora.set(horaBogota(Date.now())), 1000);
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
    clearInterval(this.relojId);
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
