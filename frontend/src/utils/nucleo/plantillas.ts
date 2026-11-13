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
import { esSemirrectaDePuntos } from './semirrecta';

export interface VocabularioTema {
  /** Con artículo: "la capitana Coral". Sin artículo para nombres solos: "Ana". */
  personajes: [string, string];
  objeto: { singular: string; plural: string; femenino: boolean };
  /** Con artículo: "el cofre" */
  lugar: string;
  /** Quien salta en la semirrecta */
  saltarin: string;
  /** Donde se guardan de 10 en 10 (decenas, fase 5b) */
  grupo: { singular: string; plural: string; femenino: boolean };
}

export const VOCABULARIO_POR_TEMA: Record<string, VocabularioTema> = {
  'tema-default': {
    personajes: ['Ana', 'Tomás'],
    objeto: { singular: 'manzana', plural: 'manzanas', femenino: true },
    lugar: 'la canasta',
    saltarin: '🐰',
    grupo: { singular: 'canasta', plural: 'canastas', femenino: true },
  },
  'tema-piratas': {
    personajes: ['la capitana Coral', 'el pirata Tomás'],
    objeto: { singular: 'moneda de oro', plural: 'monedas de oro', femenino: true },
    lugar: 'el cofre',
    saltarin: '🦜',
    grupo: { singular: 'bolsa', plural: 'bolsas', femenino: true },
  },
  'tema-astronautas': {
    personajes: ['la astronauta Luna', 'el astronauta Leo'],
    objeto: { singular: 'estrella', plural: 'estrellas', femenino: true },
    lugar: 'la nave',
    saltarin: '🚀',
    grupo: { singular: 'caja', plural: 'cajas', femenino: true },
  },
  'tema-magos': {
    personajes: ['la maga Sofía', 'el mago Iván'],
    objeto: { singular: 'esfera mágica', plural: 'esferas mágicas', femenino: true },
    lugar: 'la torre',
    saltarin: '🦉',
    grupo: { singular: 'caja', plural: 'cajas', femenino: true },
  },
  'tema-caballeros': {
    personajes: ['el caballero Andrés', 'la escudera Rosa'],
    objeto: { singular: 'escudo', plural: 'escudos', femenino: false },
    lugar: 'el castillo',
    saltarin: '🐉',
    grupo: { singular: 'fila', plural: 'filas', femenino: true },
  },
  'tema-vaqueros': {
    personajes: ['la vaquera Rosa', 'el vaquero Ramón'],
    objeto: { singular: 'caballo', plural: 'caballos', femenino: false },
    lugar: 'el rancho',
    saltarin: '🤠',
    grupo: { singular: 'corral', plural: 'corrales', femenino: false },
  },
  'tema-princesas': {
    personajes: ['la princesa Ana', 'la princesa Mía'],
    objeto: { singular: 'gema', plural: 'gemas', femenino: true },
    lugar: 'el taller',
    saltarin: '👑',
    grupo: { singular: 'cofre', plural: 'cofres', femenino: false },
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
    los: femenino ? 'las' : 'los',
    juntos: femenino ? 'juntas' : 'juntos',
    sueltos: femenino ? 'sueltas' : 'sueltos',
    /** "1 suelta", "3 sueltas" */
    nSueltos: (n: number) => `${n} ${femenino ? (n === 1 ? 'suelta' : 'sueltas') : (n === 1 ? 'suelto' : 'sueltos')}`,
    ninguno: femenino ? 'ninguna suelta' : 'ninguno suelto',
    grupo: (n: number) => `${n} ${n === 1 ? v.grupo.singular : v.grupo.plural}`,
    grupos: v.grupo.plural,
    cuantosGrupos: v.grupo.femenino ? '¿Cuántas' : '¿Cuántos',
    cadaGrupo: v.grupo.femenino ? 'cada una' : 'cada uno',
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
    const pres = p.forma === 'expresion' && p.presentacion?.tipo === 'semirrecta' && !esSemirrectaDePuntos(p.presentacion)
      ? p.presentacion : null;
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

  // ─── Numeración (fase 5b) ───
  contar: (_n, v, variante) => {
    const f = frases(v);
    return elegir([
      `${f.P1} buscó ${f.plural} en ${f.lugar}. ${f.cuantos} encontró?`,
      `Cuenta ${f.los} ${f.plural} de ${f.lugar}. ${f.cuantos} hay?`,
    ], variante);
  },
  nombre: (_n, v) => `${frases(v).P1} escribió un número con letras. ¿Qué número es?`,
  formar: ([x, y], v, variante) => {
    const f = frases(v);
    if (x >= 10 && x % 10 === 0 && y < 10) {
      return `${f.P1} tiene ${f.grupo(x / 10)} de 10 ${f.plural} y ${y === 0 ? f.ninguno : f.nSueltos(y)}. ${f.cuantos} tiene?`;
    }
    return elegir([
      `${f.P1} tiene ${f.obj(x)} en una mano y ${y} en la otra. ${f.cuantos} forman?`,
      `En ${f.lugar} hay ${f.obj(x)} de un lado y ${y} del otro. ${f.cuantos} forman ${f.juntos}?`,
    ], variante);
  },
  formar_faltante: (n, v, variante, p) => SITUACIONES.faltante_suma(n, v, variante, p),
  secuencia_progresiva: ([salto], v, _variante, p) => secuencia(v, salto, 'hacia adelante', p),
  secuencia_regresiva: ([salto], v, _variante, p) => secuencia(v, salto, 'hacia atrás', p),
  grupos_total: ([g], v) => {
    const f = frases(v);
    return `Hay ${f.grupo(g)} con 10 ${f.plural} ${f.cadaGrupo}. ${f.cuantos} ${f.plural} hay?`;
  },
  grupos_cuantos: ([total], v) => {
    const f = frases(v);
    return `${f.P1} guarda ${f.obj(total)} en ${f.grupos} de 10. ${f.cuantosGrupos} ${f.grupos} llena?`;
  },
  decenas_unidades: ([n], v) => {
    const f = frases(v);
    return `${f.P1} guarda ${f.obj(n)} en ${f.grupos} de 10. ${f.cuantosGrupos} ${f.grupos} llena y ${f.cuantos.toLowerCase().slice(1)} le sobran?`;
  },
  componer_decenas: ([d, u], v) => SITUACIONES.formar([d * 10, u], v, 0, {} as Problema),
  descomponer: ([n], v) => {
    const f = frases(v);
    return `${f.P1} quiere separar ${f.obj(n)} en decenas completas y ${f.sueltos}. ¿Cómo ${f.los} separa?`;
  },
  comparar_cantidades: ([x, y], v) => {
    const f = frases(v);
    return `${f.P1} tiene ${f.obj(x)} y ${f.p2} tiene ${y}. Compara los números: ¿quién tiene más?`;
  },
  semirrecta_leer: (_n, v) => `${frases(v).P1} se paró en la semirrecta. ¿En qué número está?`,
  semirrecta_ubicar: ([n], v) => `${frases(v).P1} busca el ${n} en la semirrecta. ¿Qué flecha lo señala?`,
  ordenar: (_n, v, _variante, p) => {
    const f = frases(v);
    const orden = p.forma === 'ordenar' && !p.ascendente ? 'de mayor a menor' : 'de menor a mayor';
    return `${f.P1} tiene estas tarjetas de números. ¿Cómo quedan ${orden}?`;
  },
};

/** "La capitana Coral cuenta de 2 en 2 hacia adelante. ¿Qué número falta?" */
function secuencia(v: VocabularioTema, salto: number, sentido: string, p: Problema): string {
  const huecos = p.forma === 'expresion' ? p.huecos.length : 1;
  const de = salto === 1 ? 'de 1 en 1' : `de ${salto} en ${salto}`;
  return `${frases(v).P1} cuenta ${de} ${sentido}. ${huecos > 1 ? '¿Qué números faltan?' : '¿Qué número falta?'}`;
}

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
  if (!p.enunciado) return null;
  const armar = SITUACIONES[p.enunciado.situacion];
  if (!armar) return null;
  const v = vocabularioDelTema(temaId);
  const texto = armar(p.enunciado.cantidades, v, p.enunciado.variante, p);
  if (p.forma !== 'expresion') return texto;
  // Con el signo oculto (no al comparar ni al elegir una flecha) la pregunta pasa a ser el resultado
  const soloSigno = !p.modos.mostrar_signo && p.huecos.length > 0 && p.huecos.every(h => h.tipo === 'opcion');
  return soloSigno ? conCierre(texto, p.enunciado.situacion, p, v) : texto;
}

export const SITUACIONES_CONOCIDAS = Object.keys(SITUACIONES);
