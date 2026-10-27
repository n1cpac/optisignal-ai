import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { EstadoLuz, Semaforo } from '../models/semaforo.model';
import { Reporte } from '../models/reporte.model';

/**
 * Simula el backend (/semaforos, /reportes y /reportes/envio) con datos falsos
 * para ver el panel funcionando. Se activa/desactiva en mock-api.config.ts.
 * Las coordenadas son intersecciones reales de la malla vial (ubicaciones de ejemplo).
 */

const IMG = 'assets/semaforos/';

interface SemaforoMock {
  id: string;
  nombre: string;
  lat: number;
  lng: number;
  falla?: boolean; // true: el semaforo presenta una anomalia
  electrico?: EstadoLuz; // luz que reporta el sistema electrico; si falta, sigue un ciclo
  imagen?: string; // captura de la camara (archivo en assets/semaforos)
  obs?: boolean; // true: su imagen en vivo viene de la camara virtual de OBS
  fase?: number; // desfase del ciclo de luces, en segundos (solo si no hay 'electrico')
}

/**
 * Cada captura muestra una luz distinta, asi que el estado electrico de estos semaforos es fijo
 * y coherente con su imagen. Solo el que usa OBS sigue el ciclo de luces.
 */
const SEMAFOROS_MOCK: SemaforoMock[] = [
  { id: 's1', nombre: 'AC 13 con CL 13', lat: 4.60357, lng: -74.07992,
    electrico: 'rojo', imagen: IMG + 'rojo-1.png' },
  // Camara virtual de OBS
  { id: 's2', nombre: 'AC 72 con KR 13', lat: 4.65843, lng: -74.06038,
    obs: true, fase: 4 },
  // Falla: el sistema electrico dice verde, pero la camara ve rojo
  { id: 's3', nombre: 'AK 7 con CL 117', lat: 4.69469, lng: -74.03265,
    falla: true, electrico: 'verde', imagen: IMG + 'rojo-2.png' },
  { id: 's4', nombre: 'AC 145 con KR 96', lat: 4.74077, lng: -74.08894,
    electrico: 'amarillo', imagen: IMG + 'amarillo.png' },
  { id: 's5', nombre: 'AC 63 con KR 103A', lat: 4.69513, lng: -74.12479,
    electrico: 'rojo', imagen: IMG + 'rojo-1.png' },
  // Falla: semaforo apagado
  { id: 's6', nombre: 'AK 97 con CL 16I', lat: 4.66986, lng: -74.14509,
    falla: true, electrico: 'apagado', imagen: IMG + 'apagado.png' },
  // Falla: rojo y verde encendidos al mismo tiempo
  { id: 's7', nombre: 'AC 6 con TV 78C', lat: 4.6323, lng: -74.14954,
    falla: true, electrico: 'rojo', imagen: IMG + 'rojo-verde.png' },
  { id: 's8', nombre: 'AK 80 con CL 59 S', lat: 4.60866, lng: -74.18121,
    electrico: 'amarillo', imagen: IMG + 'amarillo.png' }
];

function haceMinutos(min: number): string {
  return new Date(Date.now() - min * 60_000).toISOString();
}

const REPORTES_MOCK: Reporte[] = [
  { id: 'r1', semaforoId: 's6', ubicacion: 'AK 97 con CL 16I', fecha: haceMinutos(4),
    descripcion: 'Semaforo apagado: no se detecta ninguna luz encendida.' },
  { id: 'r6', semaforoId: 's7', ubicacion: 'AC 6 con TV 78C', fecha: haceMinutos(9),
    descripcion: 'Luces roja y verde encendidas al mismo tiempo.' },
  { id: 'r2', semaforoId: 's3', ubicacion: 'AK 7 con CL 117', fecha: haceMinutos(18),
    descripcion: 'El sistema electrico indica verde pero la camara ve rojo.' },
  { id: 'r3', semaforoId: 's6', ubicacion: 'AK 97 con CL 16I', fecha: haceMinutos(55),
    descripcion: 'Posible interrupcion de energia en el controlador.' },
  { id: 'r4', semaforoId: 's3', ubicacion: 'AK 7 con CL 117', fecha: haceMinutos(130),
    descripcion: 'Secuencia invalida: paso de rojo a verde sin amarillo.' },
  { id: 'r5', semaforoId: 's2', ubicacion: 'AC 72 con KR 13', fecha: haceMinutos(1500),
    descripcion: 'Baja confianza de deteccion por contraluz.' }
];

/** Ciclo simple de 20 s: verde, amarillo, rojo. */
function cicloLuz(fase: number): EstadoLuz {
  const t = (Date.now() / 1000 + fase) % 20;
  if (t < 9) return 'verde';
  if (t < 11) return 'amarillo';
  return 'rojo';
}

function generarSemaforos(): Semaforo[] {
  const ahora = new Date().toISOString();
  return SEMAFOROS_MOCK.map((s) => ({
    id: s.id,
    nombre: s.nombre,
    lat: s.lat,
    lng: s.lng,
    estadoOperativo: s.falla ? 'anomalia' : 'normal',
    estadoElectrico: s.electrico ?? cicloLuz(s.fase ?? 0),
    fuenteImagen: s.obs ? 'obs' : 'url',
    imagenUrl: s.imagen ?? '',
    ultimaActualizacion: ahora
  }));
}

function responder<T>(body: T, ms = 150): Observable<HttpResponse<T>> {
  return of(new HttpResponse({ status: 200, body })).pipe(delay(ms));
}

export const mockApiInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.method === 'GET' && req.url.endsWith('/semaforos')) {
    return responder(generarSemaforos());
  }
  if (req.method === 'GET' && req.url.endsWith('/reportes')) {
    return responder(REPORTES_MOCK);
  }
  if (req.method === 'POST' && req.url.endsWith('/reportes/envio')) {
    return responder({ ok: true }, 500);
  }
  // Cualquier otra peticion (por ejemplo el GeoJSON o las imagenes) sigue normal
  return next(req);
};
