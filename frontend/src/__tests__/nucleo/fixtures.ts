import type { ProblemaExpresion, ProblemaOrdenar } from '@/types/nucleo';

const modos = (respuesta: 'banco' | 'teclado' = 'banco', mostrar_iconos = true) => ({
  mostrar_signo: true, mostrar_iconos, respuesta, opciones_banco: 3,
});

/** 3 + 4 = _ con banco (forma de g1-u03-l01) */
export const sumaBanco: ProblemaExpresion = {
  esquema: 1, forma: 'expresion', leccion_id: 'g1-u03-l01', generador_version: 1,
  modos: modos(), iconos: [3, 4],
  segmentos: [
    { tipo: 'numero', valor: '3' }, { tipo: 'simbolo', simbolo: '+' }, { tipo: 'numero', valor: '4' },
    { tipo: 'simbolo', simbolo: '=' }, { tipo: 'hueco', hueco_id: 'resultado' },
  ],
  huecos: [{ id: 'resultado', tipo: 'numero', banco: [{ valor: '6' }, { valor: '7' }, { valor: '1' }] }],
};

/** 3 _ 4 = 7: signo oculto */
export const signoOculto: ProblemaExpresion = {
  ...sumaBanco, iconos: null, modos: { ...modos(), mostrar_signo: false, mostrar_iconos: false },
  segmentos: [
    { tipo: 'numero', valor: '3' }, { tipo: 'hueco', hueco_id: 'operador' }, { tipo: 'numero', valor: '4' },
    { tipo: 'simbolo', simbolo: '=' }, { tipo: 'numero', valor: '7' },
  ],
  huecos: [{ id: 'operador', tipo: 'opcion', opciones: [{ id: 'suma', texto: '+' }, { id: 'resta', texto: '−' }] }],
};

/** 45 _ 54: comparación */
export const comparacion: ProblemaExpresion = {
  ...signoOculto,
  segmentos: [{ tipo: 'numero', valor: '45' }, { tipo: 'hueco', hueco_id: 'rel' }, { tipo: 'numero', valor: '54' }],
  huecos: [{ id: 'rel', tipo: 'opcion', opciones: [{ id: 'menor', texto: '<' }, { id: 'mayor', texto: '>' }, { id: 'igual', texto: '=' }] }],
};

/** 23 + 14 = _ con teclado */
export const sumaTeclado: ProblemaExpresion = {
  ...sumaBanco, modos: modos('teclado', false), iconos: null,
  segmentos: [
    { tipo: 'numero', valor: '23' }, { tipo: 'simbolo', simbolo: '+' }, { tipo: 'numero', valor: '14' },
    { tipo: 'simbolo', simbolo: '=' }, { tipo: 'hueco', hueco_id: 'resultado' },
  ],
  huecos: [{ id: 'resultado', tipo: 'numero' }],
};

/** ½ + ¼ = _/_ */
export const fraccion: ProblemaExpresion = {
  ...sumaTeclado,
  segmentos: [
    { tipo: 'fraccion', numerador: 1, denominador: 2 }, { tipo: 'simbolo', simbolo: '+' },
    { tipo: 'fraccion', numerador: 1, denominador: 4 }, { tipo: 'simbolo', simbolo: '=' },
    { tipo: 'hueco', hueco_id: 'f' },
  ],
  huecos: [{ id: 'f', tipo: 'fraccion' }],
};

/** 3 h 40 min + 2 h 35 min = _ h _ min */
export const cantidad: ProblemaExpresion = {
  ...sumaTeclado,
  segmentos: [
    { tipo: 'texto', texto: '3 h 40 min' }, { tipo: 'simbolo', simbolo: '+' }, { tipo: 'texto', texto: '2 h 35 min' },
    { tipo: 'simbolo', simbolo: '=' }, { tipo: 'hueco', hueco_id: 't' },
  ],
  huecos: [{ id: 't', tipo: 'cantidad', unidades: ['h', 'min'] }],
};

export const ordenar: ProblemaOrdenar = {
  esquema: 1, forma: 'ordenar', leccion_id: 'g1-u04-l02', generador_version: 1,
  modos: modos(), iconos: null, numeros: ['15', '12', '18'], ascendente: true,
};

// ─── Fase 5a: enunciado con plantilla y semirrecta ─────────────────────────────

/** 3 + 4 = _ con enunciado "agregar" */
export const sumaConEnunciado: ProblemaExpresion = {
  ...sumaBanco,
  enunciado: { situacion: 'agregar', variante: 0, cantidades: [3, 4] },
};

/** 5 + 6 = _ en la semirrecta de 0 a 20 (resolver: sin la llegada) */
export const semirrectaResolver: ProblemaExpresion = {
  ...sumaBanco, iconos: null, modos: { ...sumaBanco.modos, mostrar_iconos: false },
  leccion_id: 'g1-u05-l05',
  segmentos: [
    { tipo: 'numero', valor: '5' }, { tipo: 'simbolo', simbolo: '+' }, { tipo: 'numero', valor: '6' },
    { tipo: 'simbolo', simbolo: '=' }, { tipo: 'hueco', hueco_id: 'resultado' },
  ],
  huecos: [{ id: 'resultado', tipo: 'numero', banco: [{ valor: '11' }, { valor: '10' }, { valor: '12' }] }],
  enunciado: { situacion: 'saltos', variante: 3, cantidades: [5, 6] },
  presentacion: {
    tipo: 'semirrecta', desde: 0, hasta: 20, marcas_cada: 1, etiquetas_cada: 1,
    inicio: 5, salto: 1, saltos: 6, sentido: 'derecha',
  },
};

/** 90 − 35 en la semirrecta, de 5 en 5, para anotar la operación: _ _ _ = _ */
export const semirrectaAnotar: ProblemaExpresion = {
  ...semirrectaResolver,
  leccion_id: 'g1-u07-l03',
  segmentos: [
    { tipo: 'hueco', hueco_id: 'numero1' }, { tipo: 'hueco', hueco_id: 'operador' },
    { tipo: 'hueco', hueco_id: 'numero2' }, { tipo: 'simbolo', simbolo: '=' }, { tipo: 'hueco', hueco_id: 'resultado' },
  ],
  huecos: [
    { id: 'numero1', tipo: 'numero', banco: [{ valor: '90' }, { valor: '55' }, { valor: '89' }] },
    { id: 'operador', tipo: 'opcion', opciones: [{ id: 'suma', texto: '+' }, { id: 'resta', texto: '−' }] },
    { id: 'numero2', tipo: 'numero', banco: [{ valor: '35' }, { valor: '30' }, { valor: '40' }] },
    { id: 'resultado', tipo: 'numero', banco: [{ valor: '55' }, { valor: '60' }, { valor: '50' }] },
  ],
  enunciado: { situacion: 'anotar_saltos', variante: 0, cantidades: [] },
  presentacion: {
    tipo: 'semirrecta', desde: 50, hasta: 100, marcas_cada: 1, etiquetas_cada: 10,
    inicio: 90, salto: 5, saltos: 7, sentido: 'izquierda', llegada: 55,
  },
};

// ─── Fase 5b: numeración ───────────────────────────────────────────────────────

/** Contar: 8 monedas (los íconos son el problema) · `Hay _` */
export const contarOcho: ProblemaExpresion = {
  ...sumaBanco, leccion_id: 'g1-u02-l01', iconos: null, modos: { ...sumaBanco.modos, mostrar_iconos: false },
  segmentos: [{ tipo: 'texto', texto: 'Hay' }, { tipo: 'hueco', hueco_id: 'resultado' }],
  huecos: [{ id: 'resultado', tipo: 'numero', banco: [{ valor: '8' }, { valor: '5' }, { valor: '9' }] }],
  enunciado: { situacion: 'contar', variante: 0, cantidades: [] },
  presentacion: { tipo: 'conteo', cantidades: [8] },
};

/** 6, 8, _, 12, 14 */
export const secuenciaDe2: ProblemaExpresion = {
  ...sumaBanco, leccion_id: 'g1-u04-l03', iconos: null,
  segmentos: [
    { tipo: 'numero', valor: '6' }, { tipo: 'texto', texto: ',' }, { tipo: 'numero', valor: '8' },
    { tipo: 'texto', texto: ',' }, { tipo: 'hueco', hueco_id: 'termino2' }, { tipo: 'texto', texto: ',' },
    { tipo: 'numero', valor: '12' }, { tipo: 'texto', texto: ',' }, { tipo: 'numero', valor: '14' },
  ],
  huecos: [{ id: 'termino2', tipo: 'numero', banco: [{ valor: '10' }, { valor: '9' }, { valor: '12' }] }],
  enunciado: { situacion: 'secuencia_progresiva', variante: 0, cantidades: [2] },
};

/** Semirrecta del 40 al 70: ¿qué número señala la flecha? (57) */
export const semirrectaLeer: ProblemaExpresion = {
  ...sumaBanco, leccion_id: 'g1-u06-l04', iconos: null,
  segmentos: [{ tipo: 'hueco', hueco_id: 'resultado' }],
  huecos: [{ id: 'resultado', tipo: 'numero', banco: [{ valor: '57' }, { valor: '53' }, { valor: '47' }] }],
  enunciado: { situacion: 'semirrecta_leer', variante: 0, cantidades: [] },
  presentacion: {
    tipo: 'semirrecta', ejercicio: 'leer', desde: 40, hasta: 70, marcas_cada: 1, etiquetas_cada: 10,
    flechas: [{ valor: 57, etiqueta: null }], ocultas: [],
  },
};

/** Semirrecta del 0 al 20 con el 12 y el 13 sin escribir; la flecha señala el 12 */
export const semirrectaLeerOcultas: ProblemaExpresion = {
  ...semirrectaLeer, leccion_id: 'g1-u04-l02',
  presentacion: {
    tipo: 'semirrecta', ejercicio: 'leer', desde: 0, hasta: 20, marcas_cada: 1, etiquetas_cada: 1,
    flechas: [{ valor: 12, etiqueta: null }], ocultas: [12, 13],
  },
};

/** El 66 está en la flecha _ (A, B o C) */
export const semirrectaUbicar: ProblemaExpresion = {
  ...sumaBanco, leccion_id: 'g1-u06-l04', iconos: null,
  segmentos: [{ tipo: 'numero', valor: '66' }, { tipo: 'simbolo', simbolo: '→' }, { tipo: 'hueco', hueco_id: 'flecha' }],
  huecos: [{ id: 'flecha', tipo: 'opcion', opciones: [{ id: 'A', texto: 'A' }, { id: 'B', texto: 'B' }, { id: 'C', texto: 'C' }] }],
  enunciado: { situacion: 'semirrecta_ubicar', variante: 0, cantidades: [66] },
  presentacion: {
    tipo: 'semirrecta', ejercicio: 'ubicar', desde: 50, hasta: 80, marcas_cada: 1, etiquetas_cada: 10,
    flechas: [{ valor: 56, etiqueta: 'A' }, { valor: 64, etiqueta: 'B' }, { valor: 66, etiqueta: 'C' }], ocultas: [],
  },
};

/** Ordenar de 2 cifras, de mayor a menor, con enunciado */
export const ordenarConEnunciado: ProblemaOrdenar = {
  ...ordenar, leccion_id: 'g1-u06-l04', numeros: ['37', '73', '45', '48'], ascendente: false,
  enunciado: { situacion: 'ordenar', variante: 0, cantidades: [] },
};
