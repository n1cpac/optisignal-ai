import { Component, Input } from '@angular/core';

/**
 * Banda de encabezado de página: campo Ledger Navy con cuadrícula (Data-Grid Backdrop),
 * reglas verticales finas y marcas "+" de registro. Plano, sin sombras.
 * Con [solapa]="true" deja espacio abajo para que una consola suba desde el borde inferior.
 */
@Component({
  selector: 'app-page-head',
  standalone: true,
  template: `
    <div class="banda" [class.banda--solapa]="solapa">
      <div class="banda__interior">
        <h1 class="banda__titulo">{{ titulo }}</h1>
        @if (descripcion) {
          <p class="banda__descripcion">{{ descripcion }}</p>
        }
      </div>
    </div>
  `,
  styles: [`
    .banda {
      position: relative;
      color: var(--color-paper-white);
      background:
        linear-gradient(to right, rgba(255, 255, 255, 0.07) 1px, transparent 1px) right top / 64px 64px,
        linear-gradient(to bottom, rgba(255, 255, 255, 0.07) 1px, transparent 1px) right top / 64px 64px,
        var(--gradient-ledger-navy);
    }

    /* Marcas "+" sobre intersecciones de la cuadrícula (anclada a la derecha) */
    .banda::before, .banda::after {
      content: "";
      position: absolute;
      width: 13px;
      height: 13px;
      pointer-events: none;
      background:
        linear-gradient(#fff, #fff) center / 13px 1px no-repeat,
        linear-gradient(#fff, #fff) center / 1px 13px no-repeat;
    }
    .banda::before { right: 57px; top: 57px; }
    .banda::after { right: 185px; top: 121px; }

    .banda__interior {
      max-width: var(--page-max-width);
      margin-inline: auto;
      padding: 56px var(--spacing-32) var(--spacing-64);
      border-inline: 1px solid rgba(255, 255, 255, 0.14);
    }

    .banda--solapa .banda__interior { padding-bottom: 128px; }

    .banda__titulo {
      font-family: var(--font-season-vf);
      font-size: 56px;
      font-weight: 515;
      line-height: 1.02;
      letter-spacing: -0.3px;
    }

    .banda__descripcion {
      max-width: 60ch;
      margin-top: var(--spacing-16);
      font-size: 20px;
      line-height: 1.4;
      letter-spacing: -0.18px;
      color: rgba(255, 255, 255, 0.82);
    }

    @media (max-width: 720px) {
      .banda::before, .banda::after { display: none; }
      .banda__interior { padding: var(--spacing-32) var(--spacing-16) var(--spacing-48); border-inline: 0; }
      .banda--solapa .banda__interior { padding-bottom: 96px; }
      .banda__titulo { font-size: 40px; }
      .banda__descripcion { font-size: 16px; }
    }
  `]
})
export class PageHeadComponent {
  @Input({ required: true }) titulo = '';
  @Input() descripcion = '';
  @Input() solapa = false;
}
