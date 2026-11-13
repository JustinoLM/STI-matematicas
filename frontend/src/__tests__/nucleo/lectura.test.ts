import { describe, expect, it } from 'vitest';
import { elegirVozEspanol, instruccion, textoParaLeer } from '@/utils/nucleo/lectura';
import { cantidad, comparacion, ordenar, signoOculto, sumaBanco, sumaTeclado } from './fixtures';

const voz = (lang: string) => ({ lang, name: lang }) as SpeechSynthesisVoice;

describe('instrucción y lectura en voz alta', () => {
  it('la instrucción depende de la forma y del modo', () => {
    expect(instruccion(sumaBanco)).toBe('Arrastra el número que falta.');
    expect(instruccion(sumaTeclado)).toBe('Escribe el número que falta.');
    expect(instruccion(signoOculto)).toBe('Arrastra el signo que va en el espacio.');
    expect(instruccion(comparacion)).toContain('mayor, menor o igual');
    expect(instruccion(ordenar)).toBe('Ordena los números de menor a mayor.');
  });

  it('la voz lee la expresión con palabras', () => {
    expect(textoParaLeer(sumaBanco)).toBe('Arrastra el número que falta. 3 más 4 es igual a ¿cuánto?');
    expect(textoParaLeer(signoOculto)).toContain('3 ¿qué signo? 4 es igual a 7');
    expect(textoParaLeer(cantidad)).toContain('¿cuántos h y cuántos min?');
    expect(textoParaLeer(ordenar)).toContain('15, 12, 18');
  });

  it('elige una voz en español, o ninguna', () => {
    expect(elegirVozEspanol([voz('en-US'), voz('fr-FR')])).toBeNull();
    expect(elegirVozEspanol([voz('en-US'), voz('es-ES'), voz('es-MX')])?.lang).toBe('es-MX');
    expect(elegirVozEspanol([voz('es-AR')])?.lang).toBe('es-AR');
  });
});
