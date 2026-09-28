import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, timer } from 'rxjs';
import { switchMap, shareReplay } from 'rxjs/operators';

import { SystemStatus } from '../models/status.model';
import { AlertRecord, AlertFilter } from '../models/alert.model';

const INTERVALO_POLLING_MS = 1500; // 1 a 2 segundos, según lo definido en el proyecto

@Injectable({ providedIn: 'root' })
export class ApiService {
  // TODO: mover a environment.ts cuando exista backend real / proxy configurado
  private readonly baseUrl = '';

  constructor(private http: HttpClient) {}

  getStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(`${this.baseUrl}/status`);
  }

  /** Polling continuo del estado del sistema (dashboard e info del sistema). */
  pollStatus(intervalMs: number = INTERVALO_POLLING_MS): Observable<SystemStatus> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getStatus()),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getAlerts(filtro?: AlertFilter): Observable<AlertRecord[]> {
    let params = new HttpParams();

    if (filtro?.tipoFalla) {
      params = params.set('tipoFalla', filtro.tipoFalla);
    }
    if (filtro?.fechaInicio) {
      params = params.set('fechaInicio', filtro.fechaInicio);
    }
    if (filtro?.fechaFin) {
      params = params.set('fechaFin', filtro.fechaFin);
    }

    return this.http.get<AlertRecord[]>(`${this.baseUrl}/alerts`, { params });
  }
}
