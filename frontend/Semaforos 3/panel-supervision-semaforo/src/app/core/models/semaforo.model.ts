/** Luz encendida segun el sistema electrico del propio semaforo. */
export type EstadoLuz = 'rojo' | 'amarillo' | 'verde' | 'apagado';
export type EstadoOperativo = 'normal' | 'anomalia';
/** 'obs': camara virtual de OBS (se abre en el navegador). 'url': imagen que entrega el backend. */
export type FuenteImagen = 'url' | 'obs';

export interface Semaforo {
  id: string;
  nombre: string; // ej. "AC 72 con KR 13"
  lat: number;
  lng: number;
  estadoOperativo: EstadoOperativo;
  estadoElectrico: EstadoLuz; // deteccion del sistema electrico del semaforo
  fuenteImagen?: FuenteImagen; // por defecto 'url'
  imagenUrl: string; // imagen en vivo de la camara (se usa cuando la fuente es 'url')
  ultimaActualizacion: string; // ISO 8601
}
