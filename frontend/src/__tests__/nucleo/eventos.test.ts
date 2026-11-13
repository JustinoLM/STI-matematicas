import { describe, expect, it } from 'vitest';
import { MAX_EVENTOS_POR_INTENTO, RegistroEventos } from '@/utils/nucleo/eventos';

function reloj() {
  let t = 1000;
  const f = () => t;
  return Object.assign(f, { avanzar: (ms: number) => { t += ms; } });
}

describe('registro de eventos', () => {
  it('cada evento lleva los ms desde que se mostró el problema', () => {
    const r = reloj();
    const reg = new RegistroEventos(r);
    r.avanzar(1500);
    reg.registrar({ tipo: 'opcion_elegida', valor: { hueco: 'resultado', valor: '7' } });
    r.avanzar(500);
    reg.usarVoz();
    r.avanzar(1000);
    const datos = reg.cerrarIntento();
    expect(datos.tiempo_ms).toBe(3000);
    expect(datos.uso_voz).toBe(true);
    expect(datos.eventos).toEqual([
      { tipo: 'opcion_elegida', valor: { hueco: 'resultado', valor: '7' }, ms: 1500 },
      { tipo: 'voz', ms: 2000 },
    ]);
  });

  it('el segundo intento cuenta su tiempo desde la corrección y lleva solo sus eventos', () => {
    const r = reloj();
    const reg = new RegistroEventos(r);
    r.avanzar(2000);
    reg.usarVoz();
    reg.cerrarIntento();
    r.avanzar(800); // el niño lee la corrección
    reg.empezarIntento();
    r.avanzar(1200);
    reg.registrar({ tipo: 'cambio_opcion', valor: { hueco: 'resultado', de: '6', a: '7' } });
    const datos = reg.cerrarIntento();
    expect(datos.tiempo_ms).toBe(1200);
    expect(datos.uso_voz).toBe(false);
    expect(datos.eventos).toEqual([{ tipo: 'cambio_opcion', valor: { hueco: 'resultado', de: '6', a: '7' }, ms: 4000 }]);
  });

  it('si el envío falla, el intento se reabre sin perder eventos ni el uso de la voz', () => {
    const r = reloj();
    const reg = new RegistroEventos(r);
    reg.usarVoz();
    const fallido = reg.cerrarIntento();
    reg.reabrir(fallido);
    r.avanzar(100);
    reg.registrar({ tipo: 'opcion_elegida', valor: 'x' });
    const datos = reg.cerrarIntento();
    expect(datos.uso_voz).toBe(true);
    expect(datos.eventos.map(e => e.tipo)).toEqual(['voz', 'opcion_elegida']);
    expect(datos.tiempo_ms).toBe(100);
  });

  it('no pasa del límite de eventos del backend', () => {
    const reg = new RegistroEventos(reloj());
    for (let i = 0; i < MAX_EVENTOS_POR_INTENTO + 20; i++) reg.registrar({ tipo: 'opcion_elegida' });
    expect(reg.cerrarIntento().eventos).toHaveLength(MAX_EVENTOS_POR_INTENTO);
  });
});
