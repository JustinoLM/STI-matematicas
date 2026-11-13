import { describe, expect, it } from 'vitest';
import {
  armarRespuestas, borrarDigito, camposDeHueco, colocarFicha, escribirDigito, fichasDeHueco,
  MAX_DIGITOS, problemaCompleto, respuestasDesdeSolucion, seArrastra,
} from '@/utils/nucleo/respuestas';
import { cantidad, fraccion, ordenar, signoOculto, sumaBanco, sumaTeclado } from './fixtures';

describe('banco y opciones', () => {
  it('colocar una ficha registra la opción elegida', () => {
    const { respuestas, eventos } = colocarFicha({}, 'resultado', '7');
    expect(respuestas).toEqual({ resultado: '7' });
    expect(eventos).toEqual([{ tipo: 'opcion_elegida', valor: { hueco: 'resultado', valor: '7' } }]);
  });

  it('cambiar la ficha antes de confirmar registra también el cambio de opción', () => {
    const { respuestas, eventos } = colocarFicha({ resultado: '6' }, 'resultado', '7');
    expect(respuestas.resultado).toBe('7');
    expect(eventos.map(e => e.tipo)).toEqual(['opcion_elegida', 'cambio_opcion']);
    expect(eventos[1].valor).toEqual({ hueco: 'resultado', de: '6', a: '7' });
  });

  it('soltar la misma ficha otra vez no registra nada', () => {
    const antes = { resultado: '7' };
    const { respuestas, eventos } = colocarFicha(antes, 'resultado', '7');
    expect(respuestas).toBe(antes);
    expect(eventos).toEqual([]);
  });

  it('las fichas salen del banco o de las opciones del hueco', () => {
    expect(fichasDeHueco(sumaBanco.huecos[0]).map(f => f.texto)).toEqual(['6', '7', '1']);
    expect(fichasDeHueco(signoOculto.huecos[0])).toEqual([{ valor: 'suma', texto: '+' }, { valor: 'resta', texto: '−' }]);
    expect(seArrastra(sumaBanco.huecos[0])).toBe(true);
    expect(seArrastra(signoOculto.huecos[0])).toBe(true);
    expect(seArrastra(sumaTeclado.huecos[0])).toBe(false);
  });
});

describe('teclado', () => {
  it('escribe y borra dígitos, sin ceros a la izquierda', () => {
    const campo = { huecoId: 'resultado' };
    let r = escribirDigito({}, campo, '0');
    r = escribirDigito(r, campo, '3');
    r = escribirDigito(r, campo, '7');
    expect(r.resultado).toBe('37');
    r = borrarDigito(r, campo);
    expect(r.resultado).toBe('3');
    r = borrarDigito(r, campo);
    expect(r.resultado).toBeUndefined();
  });

  it('ignora lo que no es un dígito y respeta el máximo', () => {
    const campo = { huecoId: 'resultado' };
    let r = escribirDigito({}, campo, 'a');
    expect(r).toEqual({});
    for (let i = 0; i < MAX_DIGITOS + 3; i++) r = escribirDigito(r, campo, '9');
    expect((r.resultado as string).length).toBe(MAX_DIGITOS);
  });

  it('las fracciones y cantidades tienen un campo por parte', () => {
    expect(camposDeHueco(fraccion.huecos[0])).toEqual([
      { huecoId: 'f', parte: 'numerador' }, { huecoId: 'f', parte: 'denominador' },
    ]);
    expect(camposDeHueco(cantidad.huecos[0]).map(c => c.parte)).toEqual(['h', 'min']);
    let r = escribirDigito({}, { huecoId: 'f', parte: 'numerador' }, '3');
    r = escribirDigito(r, { huecoId: 'f', parte: 'denominador' }, '4');
    expect(r.f).toEqual({ numerador: '3', denominador: '4' });
  });
});

describe('completo y envío', () => {
  it('solo está completo con todos los huecos llenos', () => {
    expect(problemaCompleto(sumaBanco, {})).toBe(false);
    expect(problemaCompleto(sumaBanco, { resultado: '7' })).toBe(true);
    expect(problemaCompleto(fraccion, { f: { numerador: '3', denominador: '' } })).toBe(false);
    expect(problemaCompleto(cantidad, { t: { h: '6' } })).toBe(false);
    expect(problemaCompleto(cantidad, { t: { h: '6', min: '15' } })).toBe(true);
    expect(problemaCompleto(ordenar, {}, ['15', '12', '18'])).toBe(true);
  });

  it('arma el JSON que espera el backend para cada tipo de hueco', () => {
    expect(armarRespuestas(sumaBanco, { resultado: '7' })).toEqual({ resultado: '7' });
    expect(armarRespuestas(signoOculto, { operador: 'suma' })).toEqual({ operador: 'suma' });
    expect(armarRespuestas(fraccion, { f: { numerador: '3', denominador: '4' } }))
      .toEqual({ f: { numerador: '3', denominador: '4' } });
    expect(armarRespuestas(cantidad, { t: { min: '15', h: '6' } })).toEqual({ t: { h: '6', min: '15' } });
    expect(armarRespuestas(ordenar, {}, ['12', '15', '18'])).toEqual({ orden: ['12', '15', '18'] });
  });

  it('convierte la solución del backend en valores de pantalla', () => {
    expect(respuestasDesdeSolucion(sumaBanco, { resultado: '7' })).toEqual({ resultado: '7' });
    expect(respuestasDesdeSolucion(fraccion, { f: { numerador: 3, denominador: 4 } }))
      .toEqual({ f: { numerador: '3', denominador: '4' } });
  });
});
