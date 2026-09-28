export type EstadoSemaforo = 'rojo' | 'amarillo' | 'verde';
export type EstadoOperativo = 'normal' | 'anomalia';
export type EstadoFuenteVideo = 'conectada' | 'desconectada';

export interface SystemStatus {
  semaforo: EstadoSemaforo;
  confianzaDeteccion: number; // 0-100
  estadoOperativo: EstadoOperativo;
  timestampActualizacion: string; // ISO 8601
  fuenteVideo: EstadoFuenteVideo;
  fps: number;
  usoCpu: number; // %
  usoMemoria: number; // %
  totalAlertas: number;
}
