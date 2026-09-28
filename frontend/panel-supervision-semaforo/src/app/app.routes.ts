import { Routes } from '@angular/router';

import { DashboardComponent } from './features/dashboard/dashboard.component';
import { AlertsComponent } from './features/alerts/alerts.component';
import { SystemStatusComponent } from './features/system-status/system-status.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'alerts', component: AlertsComponent },
  // loadComponent: Leaflet solo se descarga cuando el usuario entra al mapa
  { path: 'map', loadComponent: () => import('./features/map/map.component').then((m) => m.MapComponent) },
  { path: 'system-status', component: SystemStatusComponent },
  { path: '**', redirectTo: 'dashboard' }
];
