/**
 * Geometría de la semirrecta numérica (presentación especial de U5 L5, U7 L3, U4 L2 y U6 L4).
 *
 * Funciones puras: reciben la presentación que manda el backend y devuelven las marcas, los
 * números que se escriben y, según el ejercicio, los arcos de los saltos con el inicio y la
 * llegada (fase 5a) o las flechas que señalan números (fase 5b: leer y ubicar), en un sistema de
 * coordenadas fijo (viewBox). El componente Semirrecta.tsx solo dibuja.
 *
 * Como en Panamáticas: una marca por número; números de 1 en 1 hasta 20 y de 10 en 10 hasta 99;
 * sobre cada arco el conteo acumulado (1, 2, 3… o 5, 10, 15…).
 */

import type { PresentacionSemirrecta, PresentacionSemirrectaPuntos } from '@/types/nucleo';

type SemirrectaCualquiera = PresentacionSemirrecta | PresentacionSemirrectaPuntos;

/** ¿Es un ejercicio de flechas (leer o ubicar)? Los de la fase 5a no traen `ejercicio`. */
export function esSemirrectaDePuntos(p: SemirrectaCualquiera): p is PresentacionSemirrectaPuntos {
  return p.ejercicio === 'leer' || p.ejercicio === 'ubicar';
}

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

/** Escala y marcas, comunes a todos los ejercicios. Los números `ocultas` no se escriben. */
function escalaYMarcas(p: SemirrectaCualquiera, ocultas: number[] = []) {
  const rango = Math.max(p.hasta - p.desde, 1);
  const unidad = (ANCHO - 2 * MARGEN) / rango;
  const xDe = (v: number) => MARGEN + (v - p.desde) * unidad;
  const marcas: Marca[] = [];
  const paso = Math.max(p.marcas_cada, 1);
  for (let v = p.desde; v <= p.hasta; v += paso) {
    const conNumero = v % p.etiquetas_cada === 0;
    marcas.push({ valor: v, x: xDe(v), etiqueta: conNumero && !ocultas.includes(v), larga: conNumero || v % 10 === 0 });
  }
  return { unidad, xDe, marcas };
}

export function geometriaSemirrecta(
  p: PresentacionSemirrecta,
  opciones: { mostrarLlegada?: boolean } = {},
): GeometriaSemirrecta {
  const { unidad, xDe, marcas } = escalaYMarcas(p);

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

// ─── Flechas: leer y ubicar (fase 5b) ────────────────────────────────────────

export interface FlechaGeometria {
  valor: number;
  x: number;
  etiqueta: string | null;
}

/** Recuadro de un número sin escribir (U4 L2): el que señala la flecha lleva "?" */
export interface CasillaOculta {
  valor: number;
  x: number;
  senalada: boolean;
}

export interface GeometriaPuntos {
  ancho: number;
  alto: number;
  yLinea: number;
  x1Linea: number;
  x2Linea: number;
  marcas: Marca[];
  flechas: FlechaGeometria[];
  casillas: CasillaOculta[];
  /** Ancho de un recuadro oculto: cabe entre dos marcas vecinas */
  anchoCasilla: number;
  descripcion: string;
}

export function geometriaPuntos(p: PresentacionSemirrectaPuntos): GeometriaPuntos {
  const { unidad, xDe, marcas } = escalaYMarcas(p, p.ocultas);
  const flechas = p.flechas.map(f => ({ valor: f.valor, x: xDe(f.valor), etiqueta: f.etiqueta }));
  const senaladas = new Set(p.flechas.map(f => f.valor));
  const casillas = p.ocultas.map(v => ({ valor: v, x: xDe(v), senalada: senaladas.has(v) }));
  const letras = flechas.map(f => f.etiqueta).filter(Boolean);
  const descripcion = p.ejercicio === 'ubicar'
    ? `Semirrecta del ${p.desde} al ${p.hasta} con las flechas ${letras.join(', ')}.`
    : `Semirrecta del ${p.desde} al ${p.hasta}. Una flecha señala un número sin escribir.`;
  return {
    ancho: ANCHO,
    alto: ALTO,
    yLinea: Y_LINEA,
    x1Linea: MARGEN - 14,
    x2Linea: ANCHO - MARGEN + 14,
    marcas,
    flechas,
    casillas,
    anchoCasilla: Math.min(40, Math.max(18, unidad * Math.max(p.marcas_cada, 1) - 4)),
    descripcion,
  };
}
