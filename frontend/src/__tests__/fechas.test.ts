import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  diaLocalHace, fechaDelServidor, finDelDiaLocal, formatearFecha, formatearFechaHora, hoyLocal,
} from '@/lib/fechas';

afterEach(() => { vi.useRealTimers(); });

describe('fechaDelServidor', () => {
  it('lee como UTC las horas sin zona y respeta las que la traen', () => {
    expect(fechaDelServidor('2026-11-15T04:30:00').toISOString()).toBe('2026-11-15T04:30:00.000Z');
    expect(fechaDelServidor('2026-11-15T04:30:00Z').toISOString()).toBe('2026-11-15T04:30:00.000Z');
    expect(fechaDelServidor('2026-11-14T23:30:00-05:00').toISOString()).toBe('2026-11-15T04:30:00.000Z');
  });
});

describe('días de Panamá', () => {
  it('las 11:30 p. m. de Panamá siguen siendo ese día, aunque en UTC ya sea el siguiente', () => {
    expect(formatearFecha('2026-11-15T04:30:00Z', { day: 'numeric', month: 'numeric' })).toBe('11/14');
    expect(formatearFecha('2026-11-15T05:30:00Z', { day: 'numeric', month: 'numeric' })).toBe('11/15');
    expect(formatearFechaHora('2026-11-15T04:30:00Z', { hour: '2-digit', minute: '2-digit', hour12: false })).toBe('23:30');
  });

  it('una fecha sola se muestra ese mismo día', () => {
    expect(formatearFecha('2026-11-14', { day: 'numeric', month: 'numeric' })).toBe('11/14');
  });

  it('hoy y los días anteriores salen del calendario de Panamá', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-15T04:30:00Z'));   // 11:30 p. m. del 14 en Panamá
    expect(hoyLocal()).toBe('2026-11-14');
    expect(diaLocalHace(0)).toBe('2026-11-14');
    expect(diaLocalHace(14)).toBe('2026-10-31');
    vi.setSystemTime(new Date('2026-03-01T04:59:00Z'));   // 11:59 p. m. del 28 de febrero
    expect(diaLocalHace(1)).toBe('2026-02-27');
  });

  it('la fecha límite elegida en el calendario dura hasta la medianoche de Panamá', () => {
    expect(new Date(finDelDiaLocal('2026-11-20')).toISOString()).toBe('2026-11-21T04:59:59.000Z');
  });

  it('un valor inválido no rompe la pantalla', () => {
    expect(formatearFecha(null)).toBe('—');
    expect(formatearFecha('no-es-fecha')).toBe('no-es-fecha');
  });
});
