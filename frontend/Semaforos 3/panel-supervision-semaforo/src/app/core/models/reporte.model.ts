export type Destinatario = 'transito' | 'tecnicos';
export type TipoFalla = 'funcionamiento' | 'dano';

/** Lo que el operador marco al confirmar un reporte desde el panel. */
export interface OpcionesReporte {
  reporteId: string;
  fecha: string; // ISO 8601
  coincide: boolean;
  falla: boolean | null; // null en reportes anteriores a esta opcion
  destinatarios: Destinatario[];
  comentario: string | null;
  tipoFalla?: TipoFalla | null;
  semaforosAfectados?: number[];
}

export interface Reporte {
  id: string;
  semaforoId: string;
  ubicacion: string;
  fecha: string; // ISO 8601
  descripcion: string;
  automatica: boolean; // alerta del sistema de vision; si no, reporte del operador
  /** Reporte del operador: sus opciones. Alerta: las del reporte que la atendio, o null si no se ha atendido. */
  opciones: OpcionesReporte | null;
  alertasVerificadas: number; // reporte del operador: cuantas alertas verifico
  ultimaAlertaVerificada: string | null; // descripcion de la mas reciente de ellas
}

/** 'actuales': alertas del sistema sin atender y de hoy. 'historial': todo lo demas. */
export type VistaReportes = 'actuales' | 'historial';

export interface PaginaReportes {
  items: Reporte[]; // mas recientes primero
  total: number; // de toda la vista
  pagina: number; // desde 1
  tamano: number;
  ultimoId: number | null; // id mas reciente de toda la vista: si crece, llego algo nuevo
}

/** Lo que se envia al backend cuando el operador redacta el reporte. */
export interface EnvioReporte {
  semaforoId: string;
  coincide: boolean; // la deteccion electrica coincide con lo que se ve en la imagen
  falla: boolean; // el operador confirma un fallo en el semaforo
  comentario: string;
  destinatarios: Destinatario[]; // solo con fallo; puede ir vacio
  tipoFalla?: TipoFalla | null;
  semaforosAfectados?: number[];
}
