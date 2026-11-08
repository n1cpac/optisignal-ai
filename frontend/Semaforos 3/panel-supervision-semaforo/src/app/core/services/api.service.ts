import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, timer } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { Semaforo } from '../models/semaforo.model';
import { EnvioReporte, PaginaReportes, VistaReportes } from '../models/reporte.model';

const INTERVALO_SEMAFOROS_MS = 1500; // 1 a 2 segundos
const INTERVALO_REPORTES_MS = 5000;
export const TAMANO_PAGINA = 20;

@Injectable({ providedIn: 'root' })
export class ApiService {
  // TODO: mover a un archivo de entorno cuando exista el backend real
  private readonly baseUrl = '';

  constructor(private http: HttpClient) {}

  getSemaforos(): Observable<Semaforo[]> {
    return this.http.get<Semaforo[]>(`${this.baseUrl}/semaforos`);
  }

  getReportes(vista: VistaReportes, pagina: number): Observable<PaginaReportes> {
    return this.http.get<PaginaReportes>(`${this.baseUrl}/reportes`, {
      params: { vista, pagina, tamano: TAMANO_PAGINA }
    });
  }

  /** Responde con el id del reporte creado. */
  enviarReporte(envio: EnvioReporte): Observable<{ ok: boolean; id: string }> {
    return this.http.post<{ ok: boolean; id: string }>(`${this.baseUrl}/reportes/envio`, envio);
  }

  /** Avisa que el operador abrio la alerta: evita que el sistema la vuelva a enviar como recordatorio. */
  abrirAlerta(id: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`${this.baseUrl}/reportes/${id}/abrir`, {});
  }

  /** Consulta periodica. Si una peticion falla, se salta ese ciclo y sigue. */
  pollSemaforos(intervalMs = INTERVALO_SEMAFOROS_MS): Observable<Semaforo[]> {
    return timer(0, intervalMs).pipe(
      switchMap(() => this.getSemaforos().pipe(catchError(() => EMPTY)))
    );
  }

  /** Consulta periodica de la pagina actual; al cambiar de pagina se consulta de inmediato. */
  pollReportes(
    vista: VistaReportes,
    pagina$: Observable<number>,
    intervalMs = INTERVALO_REPORTES_MS
  ): Observable<PaginaReportes> {
    return pagina$.pipe(
      switchMap((pagina) =>
        timer(0, intervalMs).pipe(
          switchMap(() => this.getReportes(vista, pagina).pipe(catchError(() => EMPTY)))
        )
      )
    );
  }
}
