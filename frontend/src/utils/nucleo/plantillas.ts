/**
 * Enunciados con plantilla y tema narrativo (1.º y 2.º, sin LLM; docs/DISENO_MODULAR.md,
 * sección 3 → Funciones de IA).
 *
 * El backend elige la situación (unir, agregar, quitar, comparar…) y la variante, y manda las
 * cantidades del problema (las mismas de los íconos, nunca la respuesta). Aquí se arma el texto
 * con el vocabulario del tema activo: personajes, el objeto que se cuenta (el mismo de los íconos)
 * y un lugar. Así cambiar de tema no exige generar otro problema.
 *
 * Estilo: el de los libros Panamáticas de 1.º (oraciones cortas, una pregunta al final), con
 * textos propios.
 */

import type { Problema } from '@/types/nucleo';

export interface VocabularioTema {
  /** Con artículo: "la capitana Coral". Sin artículo para nombres solos: "Ana". */
  personajes: [string, string];
  objeto: { singular: string; plural: string; femenino: boolean };
  /** Con artículo: "el cofre" */
  lugar: string;
  /** Quien salta en la semirrecta */
  saltarin: string;
}

export const VOCABULARIO_POR_TEMA: Record<string, VocabularioTema> = {
  'tema-default': {
    personajes: ['Ana', 'Tomás'],
    objeto: { singular: 'manzana', plural: 'manzanas', femenino: true },
    lugar: 'la canasta',
    saltarin: '🐰',
  },
  'tema-piratas': {
    personajes: ['la capitana Coral', 'el pirata Tomás'],
    objeto: { singular: 'moneda de oro', plural: 'monedas de oro', femenino: true },
    lugar: 'el cofre',
    saltarin: '🦜',
  },
  'tema-astronautas': {
    personajes: ['la astronauta Luna', 'el astronauta Leo'],
    objeto: { singular: 'estrella', plural: 'estrellas', femenino: true },
    lugar: 'la nave',
    saltarin: '🚀',
  },
  'tema-magos': {
    personajes: ['la maga Sofía', 'el mago Iván'],
    objeto: { singular: 'esfera mágica', plural: 'esferas mágicas', femenino: true },
    lugar: 'la torre',
    saltarin: '🦉',
  },
  'tema-caballeros': {
    personajes: ['el caballero Andrés', 'la escudera Rosa'],
    objeto: { singular: 'escudo', plural: 'escudos', femenino: false },
    lugar: 'el castillo',
    saltarin: '🐉',
  },
  'tema-vaqueros': {
    personajes: ['la vaquera Rosa', 'el vaquero Ramón'],
    objeto: { singular: 'caballo', plural: 'caballos', femenino: false },
    lugar: 'el rancho',
    saltarin: '🤠',
  },
  'tema-princesas': {
    personajes: ['la princesa Ana', 'la princesa Mía'],
    objeto: { singular: 'gema', plural: 'gemas', femenino: true },
    lugar: 'el taller',
    saltarin: '👑',
  },
};

export function vocabularioDelTema(temaId: string | null | undefined): VocabularioTema {
  return (temaId && VOCABULARIO_POR_TEMA[temaId]) || VOCABULARIO_POR_TEMA['tema-default'];
}

const mayuscula = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** "a" + persona, con la contracción: "al pirata Tomás", "a la capitana Coral", "a Ana" */
const a = (persona: string) => (persona.startsWith('el ') ? `al ${persona.slice(3)}` : `a ${persona}`);

function elegir<T>(opciones: T[], variante: number): T {
  return opciones[((variante % opciones.length) + opciones.length) % opciones.length];
}

type Armador = (n: number[], v: VocabularioTema, variante: number, p: Problema) => string;

function frases(v: VocabularioTema) {
  const [p1, p2] = v.personajes;
  const { singular, plural, femenino } = v.objeto;
  return {
    p1,
    p2,
    P1: mayuscula(p1),
    lugar: v.lugar,
    obj: (n: number) => `${n} ${n === 1 ? singular : plural}`,
    plural,
    cuantos: femenino ? '¿Cuántas' : '¿Cuántos',
    algunos: femenino ? 'algunas' : 'algunos',
  };
}

const SITUACIONES: Record<string, Armador> = {
  unir: ([x, y], v, variante) => {
    const f = frases(v);
    return elegir([
      `${f.P1} tiene ${f.obj(x)} y ${f.p2} tiene ${y}. ${f.cuantos} ${f.plural} tienen entre los dos?`,
      `En ${f.lugar} hay ${f.obj(x)} en un grupo y ${y} en otro. ${f.cuantos} hay en total?`,
    ], variante);
  },
  agregar: ([x, y], v, variante) => {
    const f = frases(v);
    return elegir([
      `En ${f.lugar} había ${f.obj(x)}. ${f.P1} trajo ${y} más. ${f.cuantos} ${f.plural} hay ahora?`,
      `${f.P1} tenía ${f.obj(x)} y ${f.p2} le regaló ${y} más. ${f.cuantos} tiene ahora?`,
    ], variante);
  },
  quitar: ([x, y], v, variante) => {
    const f = frases(v);
    return elegir([
      `En ${f.lugar} había ${f.obj(x)}. ${f.P1} se llevó ${y}. ${f.cuantos} quedan?`,
      `${f.P1} tenía ${f.obj(x)} y le dio ${y} ${a(f.p2)}. ${f.cuantos} le quedan?`,
    ], variante);
  },
  comparar: ([x, y], v) => {
    const f = frases(v);
    return `${f.P1} tiene ${f.obj(x)} y ${f.p2} tiene ${y}. ${f.cuantos} ${f.plural} más tiene ${f.p1}?`;
  },
  faltante_suma: ([x, total], v, variante) => {
    const f = frases(v);
    return elegir([
      `${f.P1} tiene ${f.obj(x)} y quiere tener ${total}. ${f.cuantos} le faltan?`,
      `Para tener ${f.obj(total)}, ${f.p1} ya juntó ${x}. ${f.cuantos} le faltan?`,
    ], variante);
  },
  faltante_resta: ([x, quedan], v, variante) => {
    const f = frases(v);
    return elegir([
      `${f.P1} tenía ${f.obj(x)} y regaló ${f.algunos}. Ahora tiene ${quedan}. ${f.cuantos} regaló?`,
      `En ${f.lugar} había ${f.obj(x)}. Se llevaron ${f.algunos} y quedaron ${quedan}. ${f.cuantos} se llevaron?`,
    ], variante);
  },
  tres: (n, v, variante, p) => {
    const f = frases(v);
    const acciones = (p.forma === 'expresion' && p.enunciado?.acciones) || [];
    const pasos = acciones.map((accion, i) => {
      const k = n[i + 1];
      const conector = i === 0 ? 'Luego' : 'Después';
      const opciones = accion === 'agregar'
        ? [`ganó ${k} más`, `${f.p2} le dio ${k} más`]
        : [`perdió ${k}`, `le dio ${k} ${a(f.p2)}`];
      return `${conector} ${elegir(opciones, variante + i)}.`;
    });
    return `${f.P1} tenía ${f.obj(n[0])}. ${pasos.join(' ')} ${f.cuantos} tiene ahora?`;
  },
  saltos: ([x, y], v, _variante, p) => {
    const f = frases(v);
    const pres = p.forma === 'expresion' ? p.presentacion : null;
    const salto = pres?.salto ?? 1;
    const derecha = (pres?.sentido ?? 'derecha') === 'derecha';
    if (salto === 1) {
      const lado = derecha ? 'la derecha' : 'la izquierda';
      return `${f.P1} está en el ${x} y da ${y} ${y === 1 ? 'salto' : 'saltos'} hacia ${lado}. ¿A qué número llega?`;
    }
    const verbo = derecha ? 'avanza' : 'retrocede';
    return `${f.P1} está en el ${x} y ${verbo} ${y}, de ${salto} en ${salto}. ¿A qué número llega?`;
  },
  anotar_saltos: (_n, v) => {
    const f = frases(v);
    return `Mira los saltos de ${f.p1} en la semirrecta. ¿Qué operación muestran?`;
  },
};

/** Con el signo oculto el resultado ya está escrito y lo que se pregunta es el signo (lo dice la
 * instrucción): la pregunta final se cambia por una frase con el resultado, para que la historia
 * diga qué pasó ("Ana tiene 7 manzanas y Tomás tiene 1. En total hay 8."). */
const CIERRES: Record<string, (r: number, f: ReturnType<typeof frases>) => string> = {
  unir: r => `En total hay ${r}.`,
  agregar: r => `Ahora hay ${r}.`,
  quitar: r => `${r === 1 ? 'Queda' : 'Quedan'} ${r}.`,
  comparar: (r, f) => `${f.P1} tiene ${r} más.`,
  tres: r => `Al final tiene ${r}.`,
  saltos: r => `Llega al ${r}.`,
};

function conCierre(texto: string, situacion: string, p: Problema, v: VocabularioTema): string {
  const i = texto.lastIndexOf('¿');
  const historia = i > 0 ? texto.slice(0, i).trimEnd() : texto;
  const ultimo = p.forma === 'expresion' ? [...p.segmentos].reverse().find(s => s.tipo === 'numero') : undefined;
  const cierre = CIERRES[situacion];
  if (!cierre || !ultimo || ultimo.tipo !== 'numero') return historia;
  return `${historia} ${cierre(Number(ultimo.valor), frases(v))}`;
}

/** Texto del enunciado con el tema; null si el problema no trae plantilla (o es desconocida). */
export function textoEnunciado(p: Problema, temaId: string | null | undefined): string | null {
  if (p.forma !== 'expresion' || !p.enunciado) return null;
  const armar = SITUACIONES[p.enunciado.situacion];
  if (!armar) return null;
  const v = vocabularioDelTema(temaId);
  const texto = armar(p.enunciado.cantidades, v, p.enunciado.variante, p);
  const soloSigno = p.huecos.length > 0 && p.huecos.every(h => h.tipo === 'opcion');
  return soloSigno ? conCierre(texto, p.enunciado.situacion, p, v) : texto;
}

export const SITUACIONES_CONOCIDAS = Object.keys(SITUACIONES);
