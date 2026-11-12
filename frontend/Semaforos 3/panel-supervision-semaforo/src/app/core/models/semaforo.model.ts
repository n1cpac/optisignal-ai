/** Luz encendida segun el sistema electrico del propio semaforo. */
export type EstadoLuz = 'rojo' | 'amarillo' | 'verde' | 'apagado';
/** Lo que ve la camara. 'sin_deteccion': YOLO no halla el semaforo; 'sin_senal': no llega video. */
export type EstadoVisual =
  | EstadoLuz
  | 'multiple'
  | 'sin_deteccion'
  | 'desconocido'
  | 'sin_senal';
export type EstadoOperativo = 'normal' | 'anomalia';

export interface Semaforo {
  id: string;
  nombre: string; // ej. "AC 72 con KR 13"
  lat: number;
  lng: number;
  estadoOperativo: EstadoOperativo;
  estadoElectrico: EstadoLuz | 'multiple'; // deteccion del sistema electrico del semaforo
  lucesElectricas: EstadoLuz[]; // luces encendidas segun el sistema electrico
  estadoVisual: EstadoVisual; // YOLO + HSV
  lucesDetectadas: EstadoLuz[]; // lentes encendidos segun la camara
  confianza: number | null; // confianza de YOLO, de 0 a 1
  imagenUrl: string; // video en vivo de la camara (MJPEG)
  ultimaActualizacion: string; // ISO 8601
}
