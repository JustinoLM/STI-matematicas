/**
 * Estado de las respuestas de un problema del núcleo, sin React.
 *
 * - Banco y opciones: el niño arrastra una ficha al hueco (colocarFicha). Cada colocación es un
 *   evento `opcion_elegida`; si el hueco ya tenía otra ficha, además `cambio_opcion`.
 * - Teclado: se escribe dígito a dígito en el campo activo (escribirDigito / borrarDigito). Un
 *   campo es un hueco numérico, o una parte de una fracción o de una cantidad con unidades.
 * - armarRespuestas: el JSON que espera el backend ({hueco_id: respuesta} o {"orden": [...]}).
 */

import type {
  EventoNucleo,
  Hueco,
  Problema,
  Respuestas,
  ValorFraccion,
  ValorHueco,
} from '@/types/nucleo';

export const MAX_DIGITOS = 6;

/** Campo editable con el teclado: el hueco y, en fracción o cantidad, la parte */
export interface Campo {
  huecoId: string;
  parte?: string; // 'numerador' | 'denominador' | unidad
}

export const claveCampo = (c: Campo) => (c.parte ? `${c.huecoId}.${c.parte}` : c.huecoId);

export type EventoSinTiempo = Omit<EventoNucleo, 'ms'>;

// ─── Banco y opciones ────────────────────────────────────────────────────────

export function colocarFicha(
  respuestas: Respuestas,
  huecoId: string,
  valor: string,
): { respuestas: Respuestas; eventos: EventoSinTiempo[] } {
  const anterior = respuestas[huecoId];
  if (anterior === valor) return { respuestas, eventos: [] };
  const eventos: EventoSinTiempo[] = [{ tipo: 'opcion_elegida', valor: { hueco: huecoId, valor } }];
  if (typeof anterior === 'string') {
    eventos.push({ tipo: 'cambio_opcion', valor: { hueco: huecoId, de: anterior, a: valor } });
  }
  return { respuestas: { ...respuestas, [huecoId]: valor }, eventos };
}

// ─── Teclado ─────────────────────────────────────────────────────────────────

function leerCampo(respuestas: Respuestas, campo: Campo): string {
  const v = respuestas[campo.huecoId];
  if (!campo.parte) return typeof v === 'string' ? v : '';
  if (v && typeof v === 'object') return (v as Record<string, string>)[campo.parte] ?? '';
  return '';
}

function escribirCampo(respuestas: Respuestas, campo: Campo, texto: string): Respuestas {
  if (!campo.parte) return { ...respuestas, [campo.huecoId]: texto === '' ? undefined : texto };
  const actual = respuestas[campo.huecoId];
  const objeto = actual && typeof actual === 'object' ? { ...(actual as Record<string, string>) } : {};
  objeto[campo.parte] = texto;
  return { ...respuestas, [campo.huecoId]: objeto as ValorHueco };
}

export function escribirDigito(respuestas: Respuestas, campo: Campo, digito: string): Respuestas {
  if (!/^\d$/.test(digito)) return respuestas;
  const actual = leerCampo(respuestas, campo);
  if (actual.length >= MAX_DIGITOS) return respuestas;
  const nuevo = actual === '0' ? digito : actual + digito; // sin ceros a la izquierda
  return escribirCampo(respuestas, campo, nuevo);
}

export function borrarDigito(respuestas: Respuestas, campo: Campo): Respuestas {
  return escribirCampo(respuestas, campo, leerCampo(respuestas, campo).slice(0, -1));
}

export function valorCampo(respuestas: Respuestas, campo: Campo): string {
  return leerCampo(respuestas, campo);
}

/** Campos editables con teclado de un hueco, en orden */
export function camposDeHueco(h: Hueco): Campo[] {
  switch (h.tipo) {
    case 'numero':
      return [{ huecoId: h.id }];
    case 'fraccion':
      return [{ huecoId: h.id, parte: 'numerador' }, { huecoId: h.id, parte: 'denominador' }];
    case 'cantidad':
      return h.unidades.map(u => ({ huecoId: h.id, parte: u }));
    default:
      return [];
  }
}

/** ¿El hueco se responde arrastrando del banco (o sus opciones)? */
export function seArrastra(h: Hueco): boolean {
  return h.tipo === 'opcion' || (h.tipo === 'numero' && !!h.banco);
}

/** Fichas que se arrastran a un hueco: las opciones del banco o las del hueco de opción */
export function fichasDeHueco(h: Hueco): { valor: string; texto: string }[] {
  if (h.tipo === 'opcion') return h.opciones.map(o => ({ valor: o.id, texto: o.texto }));
  if (h.tipo === 'numero' && h.banco) return h.banco.map(o => ({ valor: o.valor, texto: o.valor }));
  return [];
}

// ─── Completo y envío ────────────────────────────────────────────────────────

export function huecoCompleto(h: Hueco, v: ValorHueco | undefined): boolean {
  if (v === undefined) return false;
  if (h.tipo === 'numero' || h.tipo === 'opcion') return typeof v === 'string' && v !== '';
  if (typeof v !== 'object') return false;
  if (h.tipo === 'fraccion') {
    const f = v as ValorFraccion;
    return !!f.numerador && !!f.denominador;
  }
  return h.unidades.every(u => !!(v as Record<string, string>)[u]);
}

export function problemaCompleto(p: Problema, respuestas: Respuestas, orden?: string[]): boolean {
  if (p.forma === 'ordenar') return !!orden && orden.length === p.numeros.length;
  return p.huecos.every(h => huecoCompleto(h, respuestas[h.id]));
}

export function armarRespuestas(p: Problema, respuestas: Respuestas, orden?: string[]): Record<string, unknown> {
  if (p.forma === 'ordenar') return { orden: orden ?? p.numeros };
  const salida: Record<string, unknown> = {};
  for (const h of p.huecos) {
    const v = respuestas[h.id];
    if (v === undefined) continue;
    if (h.tipo === 'fraccion') {
      const f = v as ValorFraccion;
      salida[h.id] = { numerador: f.numerador, denominador: f.denominador };
    } else if (h.tipo === 'cantidad') {
      salida[h.id] = Object.fromEntries(h.unidades.map(u => [u, (v as Record<string, string>)[u]]));
    } else {
      salida[h.id] = v;
    }
  }
  return salida;
}

/** Convierte la solución del backend (misma forma que las respuestas) en valores de pantalla */
export function respuestasDesdeSolucion(p: Problema, solucion: Record<string, unknown>): Respuestas {
  if (p.forma === 'ordenar') return {};
  const r: Respuestas = {};
  for (const h of p.huecos) {
    const s = solucion[h.id];
    if (s === undefined) continue;
    if (typeof s === 'string') r[h.id] = s;
    else if (s && typeof s === 'object') {
      r[h.id] = Object.fromEntries(Object.entries(s as Record<string, unknown>).map(([k, x]) => [k, String(x)]));
    }
  }
  return r;
}
