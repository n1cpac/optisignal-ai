/** Colombia no tiene horario de verano: siempre GMT-5, sin importar la zona del equipo. */
export const ZONA_BOGOTA = '-0500'; // para DatePipe

const FORMATO_HORA = new Intl.DateTimeFormat('es-CO', {
  timeZone: 'America/Bogota',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
});

/** HH:MM:SS en hora de Bogota; '--:--:--' si la fecha no es valida. */
export function horaBogota(fecha: Date | string | number): string {
  const f = fecha instanceof Date ? fecha : new Date(fecha);
  return Number.isNaN(f.getTime()) ? '--:--:--' : FORMATO_HORA.format(f);
}
