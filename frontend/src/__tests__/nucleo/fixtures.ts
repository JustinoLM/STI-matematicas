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
