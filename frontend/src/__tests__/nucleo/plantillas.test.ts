import { describe, expect, it } from 'vitest';
import type { ProblemaExpresion } from '@/types/nucleo';
import { instruccion, textoParaLeer } from '@/utils/nucleo/lectura';
import { ICONO_POR_TEMA } from '@/utils/nucleo/iconos';
import {
  SITUACIONES_CONOCIDAS,
  textoEnunciado,
  VOCABULARIO_POR_TEMA,
  vocabularioDelTema,
} from '@/utils/nucleo/plantillas';
import { semirrectaAnotar, semirrectaResolver, signoOculto, sumaBanco, sumaConEnunciado } from './fixtures';

const con = (situacion: string, cantidades: number[], variante = 0, extra: Partial<ProblemaExpresion> = {}) =>
  ({ ...sumaBanco, ...extra, enunciado: { ...(extra.enunciado ?? {}), situacion, variante, cantidades } }) as ProblemaExpresion;

describe('enunciados con plantilla', () => {
  it('hay vocabulario para los 6 temas y el de por defecto, los mismos que tienen ícono', () => {
    expect(Object.keys(VOCABULARIO_POR_TEMA).sort()).toEqual(Object.keys(ICONO_POR_TEMA).sort());
    expect(vocabularioDelTema('no-existe')).toBe(VOCABULARIO_POR_TEMA['tema-default']);
    expect(vocabularioDelTema(null)).toBe(VOCABULARIO_POR_TEMA['tema-default']);
  });

  it('arma el texto con el tema y las cantidades del problema', () => {
    expect(textoEnunciado(sumaConEnunciado, 'tema-piratas')).toBe(
      'En el cofre había 3 monedas de oro. La capitana Coral trajo 4 más. ¿Cuántas monedas de oro hay ahora?');
    expect(textoEnunciado(sumaConEnunciado, 'tema-default')).toBe(
      'En la canasta había 3 manzanas. Ana trajo 4 más. ¿Cuántas manzanas hay ahora?');
  });

  it('concuerda en género y número, y contrae "a el" en "al"', () => {
    const quitar = con('quitar', [5, 1], 1);
    expect(textoEnunciado(quitar, 'tema-caballeros')).toBe(
      'El caballero Andrés tenía 5 escudos y le dio 1 a la escudera Rosa. ¿Cuántos le quedan?');
    expect(textoEnunciado(quitar, 'tema-piratas')).toBe(
      'La capitana Coral tenía 5 monedas de oro y le dio 1 al pirata Tomás. ¿Cuántas le quedan?');
    expect(textoEnunciado(con('unir', [1, 2]), 'tema-vaqueros')).toMatch(/^La vaquera Rosa tiene 1 caballo y/);
  });

  it('cada situación y variante da un texto en todos los temas', () => {
    const extra: Record<string, Partial<ProblemaExpresion>> = {
      tres: { enunciado: { situacion: 'tres', variante: 0, cantidades: [8, 3, 2], acciones: ['agregar', 'quitar'] } },
      saltos: { presentacion: semirrectaResolver.presentacion },
    };
    for (const tema of Object.keys(VOCABULARIO_POR_TEMA)) {
      for (const situacion of SITUACIONES_CONOCIDAS) {
        for (const variante of [0, 1, 999]) {
          const texto = textoEnunciado(con(situacion, [8, 3, 2], variante, extra[situacion]), tema);
          expect(texto).toBeTruthy();
          expect(texto).not.toMatch(/undefined|NaN|\s{2}/);
          expect(texto!.endsWith('?')).toBe(true);
        }
      }
    }
  });

  it('tres números cuenta cada paso', () => {
    const p = con('tres', [11, 2, 7], 0, {
      enunciado: { situacion: 'tres', variante: 0, cantidades: [11, 2, 7], acciones: ['agregar', 'quitar'] },
    });
    expect(textoEnunciado(p, 'tema-default')).toBe(
      'Ana tenía 11 manzanas. Luego ganó 2 más. Después le dio 7 a Tomás. ¿Cuántas tiene ahora?');
  });

  it('semirrecta: saltos de 1 o de 5, hacia la derecha o la izquierda', () => {
    expect(textoEnunciado(semirrectaResolver, 'tema-astronautas')).toBe(
      'La astronauta Luna está en el 5 y da 6 saltos hacia la derecha. ¿A qué número llega?');
    const atras = { ...semirrectaAnotar, enunciado: { situacion: 'saltos', variante: 0, cantidades: [90, 35] } };
    expect(textoEnunciado(atras, 'tema-default')).toBe('Ana está en el 90 y retrocede 35, de 5 en 5. ¿A qué número llega?');
    expect(textoEnunciado(semirrectaAnotar, 'tema-default')).toBe(
      'Mira los saltos de Ana en la semirrecta. ¿Qué operación muestran?');
  });

  it('con el signo oculto cambia la pregunta por el resultado', () => {
    const p = { ...signoOculto, enunciado: { situacion: 'agregar', variante: 1, cantidades: [3, 4] } };
    expect(textoEnunciado(p, 'tema-default')).toBe('Ana tenía 3 manzanas y Tomás le regaló 4 más. Ahora hay 7.');
    const unir = { ...p, enunciado: { situacion: 'unir', variante: 0, cantidades: [3, 4] } };
    expect(textoEnunciado(unir, 'tema-piratas')).toBe(
      'La capitana Coral tiene 3 monedas de oro y el pirata Tomás tiene 4. En total hay 7.');
    expect(instruccion(p)).toBe('Arrastra el signo que va en el espacio.');
  });

  it('sin plantilla o con una situación desconocida no hay texto', () => {
    expect(textoEnunciado(sumaBanco, 'tema-piratas')).toBeNull();
    expect(textoEnunciado(con('otra', [1, 2]), 'tema-piratas')).toBeNull();
  });

  it('la voz lee el enunciado, la instrucción y la expresión', () => {
    expect(textoParaLeer(sumaConEnunciado, 'tema-default')).toBe(
      'En la canasta había 3 manzanas. Ana trajo 4 más. ¿Cuántas manzanas hay ahora? ' +
      'Arrastra el número que falta. 3 más 4 es igual a ¿cuánto?');
  });

  it('instrucción de los pasos y de anotar la operación', () => {
    const pasos = { ...sumaBanco, huecos: [{ id: 'paso', tipo: 'numero' }, { id: 'resultado', tipo: 'numero' }] } as ProblemaExpresion;
    expect(instruccion(pasos)).toBe('Primero forma 10. Arrastra los números que faltan.');
    expect(instruccion(semirrectaAnotar)).toBe('Arrastra los números y el signo que faltan.');
  });
});
