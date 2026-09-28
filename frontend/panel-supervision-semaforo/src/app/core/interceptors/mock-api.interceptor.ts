import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';

import { EstadoSemaforo, SystemStatus } from '../models/status.model';
import { AlertRecord } from '../models/alert.model';

/**
 * Interceptor simple que simula el backend (/status y /alerts) con datos
 * falsos, para poder ver el panel funcionando mientras no exista el backend
 * real. Se activa/desactiva desde mock-api.config.ts.
 */

const ESTADOS: EstadoSemaforo[] = ['rojo', 'amarillo', 'verde'];
let cicloIndex = 0;

const ALERTAS_MOCK: AlertRecord[] = [
  {
    id: '1',
    tipoFalla: 'Luz roja no enciende',
    fecha: '2026-09-20T08:15:00Z',
    descripcion: 'El sensor no detectó la luz roja durante 4 ciclos consecutivos.',
    fotogramaUrl: 'https://picsum.photos/seed/falla1/480/320',
    lat: 4.6486, // Av. Caracas con Calle 26 (aprox.)
    lng: -74.0664
  },
  {
    id: '2',
    tipoFalla: 'Secuencia inválida',
    fecha: '2026-09-22T14:03:00Z',
    descripcion: 'Transición directa de rojo a verde sin pasar por amarillo.',
    fotogramaUrl: 'https://picsum.photos/seed/falla2/480/320',
    lat: 4.6097, // Av. Caracas con Calle 72 (aprox.)
    lng: -74.0817
  },
  {
    id: '3',
    tipoFalla: 'Baja confianza de detección',
    fecha: '2026-09-25T19:47:00Z',
    descripcion: 'La confianza del modelo cayó por debajo del umbral (42%).',
    fotogramaUrl: 'https://picsum.photos/seed/falla3/480/320',
    lat: 4.7110, // Av. Boyacá con Calle 80 (aprox.)
    lng: -74.0721
  }
];

function generarStatusMock(): SystemStatus {
  cicloIndex = (cicloIndex + 1) % ESTADOS.length;
  const anomalia = Math.random() < 0.1;

  return {
    semaforo: ESTADOS[cicloIndex],
    confianzaDeteccion: Math.round(85 + Math.random() * 15),
    estadoOperativo: anomalia ? 'anomalia' : 'normal',
    timestampActualizacion: new Date().toISOString(),
    fuenteVideo: 'conectada',
    fps: Math.round(24 + Math.random() * 6),
    usoCpu: Math.round(20 + Math.random() * 40),
    usoMemoria: Math.round(30 + Math.random() * 30),
    totalAlertas: ALERTAS_MOCK.length
  };
}

export const mockApiInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.method === 'GET' && req.url.endsWith('/status')) {
    return of(new HttpResponse({ status: 200, body: generarStatusMock() })).pipe(delay(150));
  }

  if (req.method === 'GET' && req.url.endsWith('/alerts')) {
    let resultado = ALERTAS_MOCK;

    const tipoFalla = req.params.get('tipoFalla');
    const fechaInicio = req.params.get('fechaInicio');
    const fechaFin = req.params.get('fechaFin');

    if (tipoFalla) {
      resultado = resultado.filter((a) =>
        a.tipoFalla.toLowerCase().includes(tipoFalla.toLowerCase())
      );
    }
    if (fechaInicio) {
      resultado = resultado.filter((a) => a.fecha >= fechaInicio);
    }
    if (fechaFin) {
      resultado = resultado.filter((a) => a.fecha <= fechaFin);
    }

    return of(new HttpResponse({ status: 200, body: resultado })).pipe(delay(150));
  }

  // Cualquier otra petición sigue su curso normal
  return next(req);
};
