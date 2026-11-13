/**
 * Geometría de la semirrecta numérica (presentación especial de U5 L5 y U7 L3).
 *
 * Función pura: recibe la presentación que manda el backend y devuelve las marcas, los números
 * que se escriben, los arcos de los saltos y las posiciones del inicio y la llegada, en un
 * sistema de coordenadas fijo (viewBox). El componente Semirrecta.tsx solo dibuja.
 *
 * Como en Panamáticas: una marca por número; números de 1 en 1 hasta 20 y de 10 en 10 hasta 99;
 * sobre cada arco el conteo acumulado (1, 2, 3… o 5, 10, 15…).
 */

import type { PresentacionSemirrecta } from '@/types/nucleo';

export const ANCHO = 640;
export const ALTO = 165;
export const MARGEN = 28;
export const Y_LINEA = 100;
/** Separación mínima entre arcos para escribir su conteo encima */
export const MIN_SEPARACION_CONTEO = 16;
/** Separación mínima entre dos números de la línea; si no, el del inicio o la llegada baja una fila */
export const MIN_SEPARACION_NUMEROS = 30;

export interface Marca {
  valor: number;
  x: number;
  /** Se escribe el número debajo */
  etiqueta: boolean;
  /** Marca más alta (decenas, o las que llevan número) */
  larga: boolean;
}

export interface Arco {
  desde: number;
  hasta: number;
  x1: number;
  x2: number;
  /** Altura del arco sobre la línea */
  alto: number;
  /** Conteo acumulado que se escribe encima ("1", "2"… o "5", "10"…), o null si no cabe */
  conteo: string | null;
}

/** Número del inicio o de la llegada que no cae en una marca con número */
export interface NumeroExtra {
  valor: number;
  x: number;
  tipo: 'inicio' | 'llegada';
  /** Va en una segunda fila para no tapar el número de una marca cercana */
  abajo: boolean;
}

export interface GeometriaSemirrecta {
  ancho: number;
  alto: number;
  yLinea: number;
  x1Linea: number;
  x2Linea: number;
  marcas: Marca[];
  arcos: Arco[];
  inicio: { valor: number; x: number };
  /** Solo si la presentación la muestra */
  llegada: { valor: number; x: number } | null;
  /** Números del inicio y la llegada que no llevan ya número de marca */
  numerosExtra: NumeroExtra[];
  /** Texto para lectores de pantalla y la voz */
  descripcion: string;
}

export function llegadaDe(p: PresentacionSemirrecta): number {
  const avance = p.salto * p.saltos;
  return p.sentido === 'derecha' ? p.inicio + avance : p.inicio - avance;
}

export function geometriaSemirrecta(
  p: PresentacionSemirrecta,
  opciones: { mostrarLlegada?: boolean } = {},
): GeometriaSemirrecta {
  const rango = Math.max(p.hasta - p.desde, 1);
  const unidad = (ANCHO - 2 * MARGEN) / rango;
  const xDe = (v: number) => MARGEN + (v - p.desde) * unidad;

  const marcas: Marca[] = [];
  const paso = Math.max(p.marcas_cada, 1);
  for (let v = p.desde; v <= p.hasta; v += paso) {
    const etiqueta = v % p.etiquetas_cada === 0;
    marcas.push({ valor: v, x: xDe(v), etiqueta, larga: etiqueta || v % 10 === 0 });
  }

  const signo = p.sentido === 'derecha' ? 1 : -1;
  const separacion = p.salto * unidad;
  const altoArco = Math.min(46, Math.max(14, separacion * 0.6));
  const arcos: Arco[] = Array.from({ length: p.saltos }, (_, i) => {
    const desde = p.inicio + signo * p.salto * i;
    const hasta = desde + signo * p.salto;
    return {
      desde,
      hasta,
      x1: xDe(desde),
      x2: xDe(hasta),
      alto: altoArco,
      conteo: separacion >= MIN_SEPARACION_CONTEO ? String(p.salto * (i + 1)) : null,
    };
  });

  const llegadaValor = llegadaDe(p);
  const verLlegada = opciones.mostrarLlegada ?? p.llegada !== undefined;
  const lado = p.sentido === 'derecha' ? 'la derecha' : 'la izquierda';
  const descripcion =
    `Semirrecta del ${p.desde} al ${p.hasta}. Parte del ${p.inicio} y da ${p.saltos} ` +
    `${p.saltos === 1 ? 'salto' : 'saltos'}${p.salto > 1 ? ` de ${p.salto}` : ''} hacia ${lado}` +
    (verLlegada ? `, hasta el ${llegadaValor}.` : '.');

  const etiquetadas = marcas.filter(m => m.etiqueta);
  const numerosExtra: NumeroExtra[] = [];
  const extras: [number, 'inicio' | 'llegada'][] = [[p.inicio, 'inicio']];
  if (verLlegada) extras.push([llegadaValor, 'llegada']);
  for (const [valor, tipo] of extras) {
    if (valor % p.etiquetas_cada === 0) continue;
    const x = xDe(valor);
    const abajo = etiquetadas.some(m => Math.abs(m.x - x) < MIN_SEPARACION_NUMEROS);
    numerosExtra.push({ valor, x, tipo, abajo });
  }

  return {
    ancho: ANCHO,
    alto: ALTO,
    yLinea: Y_LINEA,
    x1Linea: MARGEN - 14,
    x2Linea: ANCHO - MARGEN + 14,
    marcas,
    arcos,
    inicio: { valor: p.inicio, x: xDe(p.inicio) },
    llegada: verLlegada ? { valor: llegadaValor, x: xDe(llegadaValor) } : null,
    numerosExtra,
    descripcion,
  };
}
