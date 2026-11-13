import { describe, expect, it } from 'vitest';
import { tamanoExpresion } from '@/utils/nucleo/expresion';
import { agruparIconos, estiloIconos, iconoDelTema, ICONO_POR_TEMA, UMBRAL_DECENAS } from '@/utils/nucleo/iconos';

describe('agrupado de íconos', () => {
  it('hasta el umbral van sueltos, en filas de 5', () => {
    expect(agruparIconos(3)).toEqual({ decenas: 0, sueltas: 3, filas: [3] });
    expect(agruparIconos(7)).toEqual({ decenas: 0, sueltas: 7, filas: [5, 2] });
    expect(agruparIconos(UMBRAL_DECENAS)).toEqual({ decenas: 0, sueltas: 10, filas: [5, 5] });
  });

  it('desde el umbral se agrupan en barras de 10 y unidades sueltas', () => {
    expect(agruparIconos(14)).toEqual({ decenas: 1, sueltas: 4, filas: [4] });
    expect(agruparIconos(20)).toEqual({ decenas: 2, sueltas: 0, filas: [] });
    expect(agruparIconos(57)).toEqual({ decenas: 5, sueltas: 7, filas: [5, 2] });
  });

  it('el umbral es configurable', () => {
    expect(agruparIconos(14, 20)).toEqual({ decenas: 0, sueltas: 14, filas: [5, 5, 4] });
    expect(agruparIconos(12, 5).decenas).toBe(1);
  });

  it('si una cantidad pasa de 10, el 10 también es una barra y las barras son compactas', () => {
    expect(estiloIconos([3, 4])).toEqual({ umbral: 10, compacto: false });
    expect(estiloIconos([10, 6])).toEqual({ umbral: 10, compacto: false });
    expect(estiloIconos([10, 30])).toEqual({ umbral: 9, compacto: true });
    expect(agruparIconos(10, estiloIconos([10, 13]).umbral)).toEqual({ decenas: 1, sueltas: 0, filas: [] });
    expect(estiloIconos([15, 4])).toEqual({ umbral: 9, compacto: true });
  });

  it('cero o negativos no dibujan nada', () => {
    expect(agruparIconos(0)).toEqual({ decenas: 0, sueltas: 0, filas: [] });
    expect(agruparIconos(-3)).toEqual({ decenas: 0, sueltas: 0, filas: [] });
  });

  it('el ícono sale del tema narrativo, con uno por defecto', () => {
    expect(iconoDelTema('tema-piratas')).toBe(ICONO_POR_TEMA['tema-piratas']);
    expect(iconoDelTema('tema-que-no-existe')).toBe(ICONO_POR_TEMA['tema-default']);
    expect(iconoDelTema(null)).toBe(ICONO_POR_TEMA['tema-default']);
  });
});

describe('largo de la expresión', () => {
  const n = (valor: string) => ({ tipo: 'numero' as const, valor });
  const sim = (simbolo: string) => ({ tipo: 'simbolo' as const, simbolo });
  const hueco = { tipo: 'hueco' as const, hueco_id: 'resultado' };
  it('3 + 4 = _ es normal; 10 + 30 = _ larga; los pasos muy larga', () => {
    expect(tamanoExpresion([n('3'), sim('+'), n('4'), sim('='), hueco])).toBe('normal');
    expect(tamanoExpresion([n('10'), sim('+'), n('30'), sim('='), hueco])).toBe('larga');
    expect(tamanoExpresion([n('9'), sim('+'), n('4'), sim('='), n('10'), sim('+'), hueco, sim('='), hueco]))
      .toBe('muy_larga');
  });
});
