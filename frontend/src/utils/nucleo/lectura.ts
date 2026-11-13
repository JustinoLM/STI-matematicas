/**
 * Instrucción del problema y texto para la lectura en voz alta.
 *
 * La instrucción es genérica según la forma del problema ("Arrastra el número que falta."). Desde
 * la fase 5a, si el problema trae enunciado con plantilla, la pantalla muestra primero ese texto
 * con el tema del estudiante, y la voz lee el enunciado, la instrucción y la expresión.
 */

import type { Hueco, Problema, Segmento } from '@/types/nucleo';
import { textoEnunciado } from './plantillas';

const SIMBOLOS_LEIDOS: Record<string, string> = {
  '+': 'más',
  '−': 'menos',
  '-': 'menos',
  '×': 'por',
  '÷': 'entre',
  '=': 'es igual a',
  '<': 'es menor que',
  '>': 'es mayor que',
};

const RELACIONES = new Set(['<', '>', '=']);

function esHuecoDeSigno(h: Hueco): boolean {
  return h.tipo === 'opcion';
}

function esComparacion(h: Hueco): boolean {
  return h.tipo === 'opcion' && h.opciones.every(o => RELACIONES.has(o.texto));
}

export function instruccion(p: Problema): string {
  if (p.forma === 'ordenar') {
    return p.ascendente ? 'Ordena los números de menor a mayor.' : 'Ordena los números de mayor a menor.';
  }
  const arrastra = p.modos.respuesta === 'banco';
  if (p.huecos.length > 0 && p.huecos.every(esHuecoDeSigno)) {
    return p.huecos.some(esComparacion)
      ? 'Arrastra el signo que va en el espacio: mayor, menor o igual.'
      : 'Arrastra el signo que va en el espacio.';
  }
  const verbo = arrastra ? 'Arrastra' : 'Escribe';
  if (p.huecos.some(h => h.id === 'paso')) return `Primero forma 10. ${verbo} los números que faltan.`;
  if (p.huecos.some(esHuecoDeSigno)) return `${verbo} los números y el signo que faltan.`;
  const varios = p.huecos.length > 1;
  return varios ? `${verbo} los números que faltan.` : `${verbo} el número que falta.`;
}

function leerSegmento(s: Segmento, huecos: Map<string, Hueco>): string {
  switch (s.tipo) {
    case 'texto':
      return s.texto;
    case 'numero':
      return s.valor;
    case 'fraccion':
      return `${s.numerador} sobre ${s.denominador}`;
    case 'simbolo':
      return SIMBOLOS_LEIDOS[s.simbolo] ?? s.simbolo;
    case 'hueco': {
      const h = huecos.get(s.hueco_id);
      if (h && h.tipo === 'opcion') return '¿qué signo?';
      if (h && h.tipo === 'cantidad') return `¿cuántos ${h.unidades.join(' y cuántos ')}?`;
      return '¿cuánto?';
    }
  }
}

/** Lo que dice la voz: el enunciado (si hay), la instrucción y la expresión
 * ("Ana tiene 3 manzanas… Arrastra el número que falta. 3 más 4 es igual a ¿cuánto?") */
export function textoParaLeer(p: Problema, temaId?: string | null): string {
  if (p.forma === 'ordenar') return `${instruccion(p)} ${p.numeros.join(', ')}.`;
  const huecos = new Map(p.huecos.map(h => [h.id, h]));
  const expresion = p.segmentos.map(s => leerSegmento(s, huecos)).join(' ');
  const enunciado = textoEnunciado(p, temaId);
  return `${enunciado ? `${enunciado} ` : ''}${instruccion(p)} ${expresion}`;
}

/** Elige una voz en español; null si el navegador no tiene ninguna */
export function elegirVozEspanol(voces: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const es = voces.filter(v => v.lang?.toLowerCase().startsWith('es'));
  if (es.length === 0) return null;
  const preferencia = ['es-pa', 'es-419', 'es-mx', 'es-us', 'es-co', 'es-es'];
  for (const lang of preferencia) {
    const v = es.find(x => x.lang.toLowerCase().replace('_', '-') === lang);
    if (v) return v;
  }
  return es[0];
}
