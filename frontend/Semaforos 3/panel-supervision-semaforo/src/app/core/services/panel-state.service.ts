import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ApiService } from './api.service';
import { Semaforo } from '../models/semaforo.model';
import { Reporte } from '../models/reporte.model';

/**
 * Estado compartido del panel: lo consultan el historial, el mapa y el detalle.
 * Aqui vive el polling, asi hay una sola consulta aunque se muestre en varios sitios.
 */
@Injectable({ providedIn: 'root' })
export class PanelStateService {
  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  readonly semaforos = signal<Semaforo[]>([]);
  readonly reportes = signal<Reporte[]>([]);
  readonly seleccionadoId = signal<string | null>(null);

  readonly seleccionado = computed(
    () => this.semaforos().find((s) => s.id === this.seleccionadoId()) ?? null
  );

  /** Totales para el recuadro del mapa. */
  readonly resumen = computed(() => {
    const lista = this.semaforos();
    const conFallas = lista.filter((s) => s.estadoOperativo === 'anomalia').length;
    return { total: lista.length, activos: lista.length - conFallas, conFallas };
  });

  constructor() {
    this.api
      .pollSemaforos()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((lista) => this.semaforos.set(lista));

    this.api
      .pollReportes()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((lista) => this.reportes.set(lista));
  }

  seleccionar(id: string | null): void {
    this.seleccionadoId.set(id);
  }
}
