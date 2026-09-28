export interface AlertRecord {
  id: string;
  tipoFalla: string;
  fecha: string; // ISO 8601
  descripcion?: string;
  fotogramaUrl?: string;
  /** Coordenadas WGS84 del semáforo que generó la alerta (necesarias para el mapa). */
  lat?: number;
  lng?: number;
}

export interface AlertFilter {
  tipoFalla?: string;
  fechaInicio?: string; // ISO 8601 (yyyy-MM-dd)
  fechaFin?: string; // ISO 8601 (yyyy-MM-dd)
}
