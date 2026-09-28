import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="cabecera">
      <div class="cabecera__interior">
        <a class="logo" routerLink="/dashboard" aria-label="Supervisión de semáforos, ir al panel principal">
          <span class="logo__marca" aria-hidden="true"></span>
          <span class="logo__texto">Supervisión de semáforos</span>
        </a>

        <nav class="nav" aria-label="Principal">
          <a routerLink="/dashboard" routerLinkActive="nav__enlace--activo">Panel principal</a>
          <a routerLink="/alerts" routerLinkActive="nav__enlace--activo">Alertas</a>
          <a routerLink="/map" routerLinkActive="nav__enlace--activo">Mapa</a>
          <a routerLink="/system-status" routerLinkActive="nav__enlace--activo">Info. del sistema</a>
        </nav>
      </div>
    </header>

    <main>
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [`
    /* Cabecera clara y fija (Light Sticky Header): 80px, regla de 1px, sin sombra.
       z-index alto para quedar sobre los controles de Leaflet (hasta 1000). */
    .cabecera {
      position: sticky;
      top: 0;
      z-index: 2000;
      background: var(--color-paper-white);
      border-bottom: 1px solid var(--color-rule-gray);
    }

    .cabecera__interior {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--spacing-24);
      max-width: var(--page-max-width);
      min-height: 80px;
      margin-inline: auto;
      padding-inline: var(--spacing-32);
    }

    .logo { display: flex; align-items: center; gap: var(--spacing-12); text-decoration: none; flex: none; }

    /* Marca: cuadrado Registry Blue con signo "+" (marca de registro) */
    .logo__marca {
      width: 28px;
      height: 28px;
      border-radius: var(--radius-controls);
      background:
        linear-gradient(#fff, #fff) center / 14px 2px no-repeat,
        linear-gradient(#fff, #fff) center / 2px 14px no-repeat,
        var(--color-registry-blue);
    }

    .logo__texto { font-size: 18px; font-weight: 500; letter-spacing: -0.02em; }

    .nav { display: flex; gap: var(--spacing-4); }

    .nav a {
      padding: 10px 14px;
      border: 1px solid transparent;
      border-radius: var(--radius-controls);
      font-size: 15px;
      font-weight: 500;
      line-height: 1.2;
      text-decoration: none;
      white-space: nowrap;
      transition: background-color 120ms, border-color 120ms;
    }

    .nav a:hover { background: var(--color-mint-paper); }

    .nav .nav__enlace--activo { border-color: var(--color-steel-rule); color: var(--color-registry-blue); }

    @media (max-width: 900px) {
      .cabecera__interior { flex-wrap: wrap; gap: var(--spacing-8); padding: var(--spacing-12) var(--spacing-16) 0; }
      .nav { width: 100%; overflow-x: auto; padding-bottom: var(--spacing-12); }
    }
  `]
})
export class AppComponent {}
