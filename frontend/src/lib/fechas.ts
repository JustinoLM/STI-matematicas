/**
 * Fechas en un solo lugar (fase 7a).
 *
 * - El backend manda las horas en UTC con «Z». Las fechas sin hora («2026-11-14») son días del
 *   colegio.
 * - Todo se muestra en la hora de Panamá, aunque el navegador esté en otra zona: la regla de
 *   dominio, la racha y los trimestres cuentan días de Panamá, y la pantalla debe coincidir.
 */

export const ZONA_COLEGIO = 'America/Panama';
// Panamá no tiene horario de verano: el desfase es fijo.
const DESFASE_COLEGIO = '-05:00';

/** Convierte lo que manda el servidor en Date. Acepta horas sin zona (se toman como UTC). */
export function fechaDelServidor(iso: string): Date {
  // Un día sin hora: mediodía de Panamá, así se muestra ese mismo día en la zona del colegio
  if (iso.length === 10) return new Date(`${iso}T12:00:00${DESFASE_COLEGIO}`);
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`);
}

/** Fecha (sin hora) en la zona del colegio. */
export function formatearFecha(
  iso: string | null | undefined,
  opciones: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' },
  idioma = 'es-PA',
): string {
  if (!iso) return '—';
  const d = fechaDelServidor(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(idioma, { ...opciones, timeZone: ZONA_COLEGIO });
}

/** Fecha y hora en la zona del colegio. */
export function formatearFechaHora(
  iso: string | null | undefined,
  opciones: Intl.DateTimeFormatOptions = { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' },
  idioma = 'es-PA',
): string {
  if (!iso) return '—';
  const d = fechaDelServidor(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(idioma, { ...opciones, timeZone: ZONA_COLEGIO });
}

/** «AAAA-MM-DD» del día del colegio para un instante (por defecto, ahora). */
export function diaDelColegio(momento: Date = new Date()): string {
  // en-CA da el formato ISO (AAAA-MM-DD)
  return new Intl.DateTimeFormat('en-CA', { timeZone: ZONA_COLEGIO, year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(momento);
}

/** Hoy en Panamá, «AAAA-MM-DD» (claves diarias de caché, mínimo de un selector de fecha). */
export function hoyLocal(): string {
  return diaDelColegio();
}

/** Año en curso en Panamá. */
export function anioLocal(): number {
  return Number(hoyLocal().slice(0, 4));
}

/** El día del colegio de hace `dias` días, «AAAA-MM-DD». */
export function diaLocalHace(dias: number): string {
  const [a, m, d] = hoyLocal().split('-').map(Number);
  const fecha = new Date(Date.UTC(a, m - 1, d - dias));
  return fecha.toISOString().slice(0, 10);
}

/** Último instante de un día del colegio, con zona (para fechas límite elegidas en un calendario). */
export function finDelDiaLocal(dia: string): string {
  return `${dia}T23:59:59${DESFASE_COLEGIO}`;
}
