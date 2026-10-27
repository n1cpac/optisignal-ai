import { Component } from '@angular/core';

import { ReportHistoryComponent } from './features/report-history/report-history.component';
import { CityMapComponent } from './features/city-map/city-map.component';
import { SemaforoDetailComponent } from './features/semaforo-detail/semaforo-detail.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ReportHistoryComponent, CityMapComponent, SemaforoDetailComponent],
  template: `
    <div class="app">
      <header class="encabezado">OPTISIGNAL</header>

      <div class="cuerpo">
        <aside class="izquierda"><app-report-history /></aside>
        <main class="centro"><app-city-map /></main>
        <aside class="derecha"><app-semaforo-detail /></aside>
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
      grid-template-columns: minmax(240px, 15%) 1fr minmax(300px, 20%);
      min-height: 0;
    }
    .izquierda, .derecha { background: #222; color: #fff; overflow-y: auto; }
    .derecha { padding: 16px; }
    .centro { position: relative; min-width: 0; background: #fff; }
  `]
})
export class AppComponent {}
