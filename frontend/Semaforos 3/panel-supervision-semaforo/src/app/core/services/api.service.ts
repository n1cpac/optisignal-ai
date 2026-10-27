import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, timer } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { Semaforo } from '../models/semaforo.model';
import { EnvioReporte, Reporte } from '../models/reporte.model';

const INTERVALO_SEMAFOROS_MS = 1500; // 1 a 2 segundos
const INTERVALO_REPORTES_MS = 5000;

@Injectable({ providedIn: 'root' })
export class ApiService {
  // TODO: mover a un archivo de entorno cuando exista el backend real
  private readonly baseUrl = '';

  constructor(private http: HttpClient) {}

  getSemaforos(): Observable<Semaforo[]> {
    return this.http.get<Semaforo[]>(`${this.baseUrl}/semaforos`);
  }

  getReportes(): Observable<Reporte[]> {
    return this.http.get<Reporte[]>(`${this.baseUrl}/reportes`);
  }

  enviarReporte(envio: EnvioReporte): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${this.baseUrl}/reportes/envio`, envio);
  }

  /** Consulta periodica. Si una peticion falla, se salta ese ciclo y sigue. */
  pollSemaforos(intervalMs = INTERVALO_SEMAFOROS_MS): Observable<Semaforo[]> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getSemaforos().pipe(catchError(() => EMPTY)))
    );
  }

  pollReportes(intervalMs = INTERVALO_REPORTES_MS): Observable<Reporte[]> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getReportes().pipe(catchError(() => EMPTY)))
    );
  }
}
