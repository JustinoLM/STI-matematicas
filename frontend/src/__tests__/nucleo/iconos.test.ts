import { describe, expect, it } from 'vitest';
import { agruparIconos, iconoDelTema, ICONO_POR_TEMA, UMBRAL_DECENAS } from '@/utils/nucleo/iconos';

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
