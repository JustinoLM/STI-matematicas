/**
 * Instrucción del problema y texto para la lectura en voz alta.
 *
 * En la fase 4 la instrucción es genérica según la forma del problema; los enunciados con
 * plantilla y tema narrativo llegan con los generadores de la fase 5.
 */

import type { Hueco, Problema, Segmento } from '@/types/nucleo';

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
  const varios = p.huecos.length > 1;
  if (arrastra) return varios ? 'Arrastra los números que faltan.' : 'Arrastra el número que falta.';
  return varios ? 'Escribe los números que faltan.' : 'Escribe el número que falta.';
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

/** Lo que dice la voz: la instrucción y la expresión ("3 más 4 es igual a ¿cuánto?") */
export function textoParaLeer(p: Problema): string {
  if (p.forma === 'ordenar') return `${instruccion(p)} ${p.numeros.join(', ')}.`;
  const huecos = new Map(p.huecos.map(h => [h.id, h]));
  const expresion = p.segmentos.map(s => leerSegmento(s, huecos)).join(' ');
  return `${instruccion(p)} ${expresion}`;
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
