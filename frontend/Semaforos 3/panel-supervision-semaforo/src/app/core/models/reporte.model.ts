export interface Reporte {
  id: string;
  semaforoId: string;
  ubicacion: string;
  fecha: string; // ISO 8601
  descripcion: string;
}

export type Destinatario = 'transito' | 'tecnicos';

/** Lo que se envia al backend cuando el operador redacta el reporte. */
export interface EnvioReporte {
  semaforoId: string;
  coincide: boolean; // la deteccion electrica coincide con lo que se ve en la imagen
  comentario: string;
  destinatarios: Destinatario[];
}
