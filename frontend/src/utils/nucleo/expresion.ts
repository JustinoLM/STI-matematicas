/** Medidas de la expresión con huecos para la pantalla. */

import type { Segmento } from '@/types/nucleo';

export type TamanoExpresion = 'normal' | 'larga' | 'muy_larga';

/** Caracteres que ocupa la expresión (un hueco vale 2) */
export function anchoExpresion(segmentos: Segmento[]): number {
  return segmentos.reduce((n, s) => {
    if (s.tipo === 'numero') return n + s.valor.length;
    if (s.tipo === 'hueco') return n + 2;
    if (s.tipo === 'texto') return n + s.texto.length;
    return n + 1;
  }, 0);
}

/**
 * Tamaño de letra de la expresión para que quepa en una línea en la columna izquierda de la
 * tablet horizontal: `3 + 4 = _` normal; `10 + 30 = _` larga; los pasos de la estrategia
 * (`9 + 4 = 10 + _ = _`) y tres números de dos cifras, muy larga. Los huecos no cambian de
 * tamaño: siguen siendo blancos grandes para soltar con el dedo.
 */
export function tamanoExpresion(segmentos: Segmento[]): TamanoExpresion {
  const ancho = anchoExpresion(segmentos);
  if (ancho > 10) return 'muy_larga';
  return ancho > 7 ? 'larga' : 'normal';
}
