import { DestroyRef, Injectable, WritableSignal, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';

import { ApiService, TAMANO_PAGINA } from './api.service';
import { Semaforo } from '../models/semaforo.model';
import { PaginaReportes, Reporte, VistaReportes } from '../models/reporte.model';

function paginaVacia(): PaginaReportes {
  return { items: [], total: 0, pagina: 1, tamano: TAMANO_PAGINA, ultimoId: null };
}

/**
 * Estado compartido del panel: lo consultan el historial, el mapa y el detalle.
 * Aqui vive el polling, asi hay una sola consulta aunque se muestre en varios sitios.
 */
@Injectable({ providedIn: 'root' })
export class PanelStateService {
  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  readonly semaforos = signal<Semaforo[]>([]);
  /** Alertas del sistema sin atender y de hoy (el backend decide que es "hoy" y que esta atendido). */
  readonly actuales = signal<PaginaReportes>(paginaVacia());
  /** Todo lo demas: alertas atendidas o de dias anteriores, y reportes del operador. */
  readonly historial = signal<PaginaReportes>(paginaVacia());
  readonly paginaActuales = signal(1);
  readonly paginaHistorial = signal(1);
  /** Semaforos con una alerta que llego mientras el panel estaba abierto y aun no se ha abierto. */
  readonly alertasNuevas = signal<ReadonlySet<string>>(new Set());
  /** Llego alguna alerta nueva (aunque este en otra pagina): la pestana "Actuales" lo avisa. */
  readonly hayAlertaNueva = signal(false);
  /** Ultimo id de alerta ya visto; null hasta la primera consulta, que no cuenta como nueva. */
  private ultimoIdVisto: number | null = null;
  /** Reporte recien creado desde el historial, que se abrira cuando llegue en la consulta. */
  private abrirAlLlegar: string | null = null;
  readonly seleccionadoId = signal<string | null>(null);
  /** Reporte del historial abierto en el panel derecho (no mueve el mapa). Excluye a seleccionadoId. */
  readonly reporteHistorial = signal<Reporte | null>(null);
  /** La camara ocupa media pantalla y el mapa se achica. */
  readonly camaraExpandida = signal(false);

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

    this.consultar('actuales', this.paginaActuales, this.actuales);
    this.consultar('historial', this.paginaHistorial, this.historial);
  }

  private consultar(
    vista: VistaReportes,
    pagina: WritableSignal<number>,
    destino: WritableSignal<PaginaReportes>
  ): void {
    this.api
      .pollReportes(vista, toObservable(pagina))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((resultado) => {
        // Si la vista se encogio (alertas atendidas) y la pagina quedo vacia, ir a la ultima con datos
        const ultima = Math.max(1, Math.ceil(resultado.total / resultado.tamano));
        if (resultado.pagina > ultima) pagina.set(ultima);
        else destino.set(resultado);
        if (vista === 'actuales') this.detectarNuevas(resultado);
        // Tras verificar desde el historial se abre la entrada nueva; si no, se refresca la abierta
        if (vista === 'historial') {
          const buscado = this.abrirAlLlegar ?? this.reporteHistorial()?.id;
          const encontrado = resultado.items.find((r) => r.id === buscado);
          if (encontrado) {
            this.reporteHistorial.set(encontrado);
            this.abrirAlLlegar = null;
          }
        }
      });
  }

  /**
   * Una alerta es nueva si su id supera el ultimo ya visto. Por id y no por fila: al cambiar de pagina
   * aparecen filas que no se habian visto, pero no son nuevas.
   */
  private detectarNuevas(resultado: PaginaReportes): void {
    const previo = this.ultimoIdVisto;
    if (resultado.ultimoId === null || (previo !== null && resultado.ultimoId <= previo)) return;
    this.ultimoIdVisto = resultado.ultimoId;
    if (previo === null) return;

    this.hayAlertaNueva.set(true);
    const nuevas = resultado.items.filter((r) => Number(r.id) > previo).map((r) => r.semaforoId);
    if (nuevas.length) this.alertasNuevas.update((actual) => new Set([...actual, ...nuevas]));
  }

  /** El operador abrio la alerta de este semaforo: se apaga su senal. */
  marcarVista(semaforoId: string): void {
    this.alertasNuevas.update((actual) => {
      const resto = new Set(actual);
      resto.delete(semaforoId);
      return resto;
    });
    this.hayAlertaNueva.set(false);
  }

  seleccionar(id: string | null): void {
    this.reporteHistorial.set(null);
    this.seleccionadoId.set(id);
  }

  /** Abre un reporte del historial en el panel derecho sin mover el mapa ni mostrar la camara en vivo. */
  verReporteHistorial(reporte: Reporte): void {
    this.abrirAlLlegar = null;
    this.seleccionadoId.set(null);
    this.reporteHistorial.set(reporte);
  }

  /**
   * Se verifico una alerta desde el historial: esa alerta sale de la lista y entra el reporte nuevo,
   * que se abre en cuanto llegue (va primero en la pagina 1).
   */
  abrirReporteNuevo(id: string): void {
    this.abrirAlLlegar = id;
    this.paginaHistorial.set(1);
  }
}
