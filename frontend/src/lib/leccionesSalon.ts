/**
 * Lógica pura de la pantalla "Lecciones del salón" (fase 6a): filtrar y agrupar el catálogo,
 * contar prioritarias y describir cada lección en lenguaje de docente.
 */

import type { ConfigLeccion, LeccionSalon, ModoLeccion } from '@/types/nucleo';

export const MAX_PRIORITARIAS = 3;

export interface UnidadCatalogo {
  clave: string;
  grado: number;
  numero: number;
  titulo: string;
  lecciones: LeccionSalon[];
}

/** Lecciones del grado (o solo las habilitadas de todos los grados), agrupadas por unidad en el
 * orden del programa. */
export function agruparPorUnidad(
  catalogo: LeccionSalon[],
  { grado, soloHabilitadas }: { grado: number; soloHabilitadas: boolean },
): UnidadCatalogo[] {
  const filtradas = catalogo
    .filter((l) => (soloHabilitadas ? l.habilitada : l.grado === grado))
    .sort((a, b) => a.orden_programa - b.orden_programa);
  const unidades: UnidadCatalogo[] = [];
  for (const l of filtradas) {
    const clave = `${l.grado}-${l.unidad_numero}`;
    let u = unidades.find((x) => x.clave === clave);
    if (!u) {
      u = { clave, grado: l.grado, numero: l.unidad_numero, titulo: l.unidad_titulo, lecciones: [] };
      unidades.push(u);
    }
    u.lecciones.push(l);
  }
  return unidades;
}

export const prioritarias = (catalogo: LeccionSalon[]) => catalogo.filter((l) => l.habilitada && l.prioritaria);

/** Habilitadas por grado, para avisar cuántas hay en otros grados */
export function habilitadasPorGrado(catalogo: LeccionSalon[]): Record<number, number> {
  const r: Record<number, number> = {};
  for (const l of catalogo) if (l.habilitada) r[l.grado] = (r[l.grado] ?? 0) + 1;
  return r;
}

/** Se puede marcar como prioritaria si ya lo es o si hay menos del máximo */
export function puedeSerPrioritaria(catalogo: LeccionSalon[], leccionId: string): boolean {
  const otras = prioritarias(catalogo).filter((l) => l.id !== leccionId);
  return otras.length < MAX_PRIORITARIAS;
}

export const configDe = (l: LeccionSalon): ConfigLeccion => ({
  signo: l.signo, iconos: l.iconos, pistas: { ...l.pistas }, prioritaria: l.prioritaria,
});

/** "naturales.suma" → "suma" */
export const habilidad = (camino: string) => camino.split('.').slice(1).join('.') || camino;

export interface Insignia {
  texto: string;
  detalle?: string;
  tono: 'gris' | 'ambar' | 'azul';
}

export function insignias(l: LeccionSalon): Insignia[] {
  const r: Insignia[] = [];
  if (!l.incluida) return r;
  if (l.parcial) r.push({ texto: 'Parcial', detalle: l.nota_parcial ?? undefined, tono: 'ambar' });
  if (l.cubierta_por === 'sistema_decimales') {
    r.push({ texto: 'Se practica en decimales', detalle: 'Esta lección la cubre la práctica de decimales.', tono: 'azul' });
  } else if (l.cubierta_por === 'modulo_regla_de_tres') {
    r.push({ texto: 'Se practica en Regla de tres', tono: 'azul' });
  } else if (!l.tiene_generador) {
    r.push({
      texto: 'Sin ejercicios todavía',
      detalle: 'Puedes habilitarla, pero no aparecerá en la práctica hasta que tenga ejercicios.',
      tono: 'gris',
    });
  }
  return r;
}

export const TEXTO_MODO: Record<'signo' | 'iconos', Record<ModoLeccion, string>> = {
  signo: { siempre: 'Signo visible', nunca: 'Signo oculto', azar: 'Signo a veces oculto' },
  iconos: { siempre: 'Con dibujos', nunca: 'Sin dibujos', azar: 'Dibujos a veces' },
};

/** Resumen corto de la configuración, para la fila del catálogo */
export function resumenConfig(l: LeccionSalon): string {
  const partes: string[] = [];
  if (l.signo !== 'siempre') partes.push(TEXTO_MODO.signo[l.signo]);
  if (l.iconos !== 'siempre') partes.push(TEXTO_MODO.iconos[l.iconos]);
  const sinPistas = (['1', '2', '3'] as const).filter((n) => !l.pistas[n]);
  if (sinPistas.length === 3) partes.push('Sin pistas');
  else if (sinPistas.length) partes.push(`Sin pista ${sinPistas.join(' y ')}`);
  return partes.join(' · ');
}

/** Nombre corto de una lección para listas: "1.º U3 L1 · Sumemos de forma horizontal" */
export const nombreLeccion = (l: Pick<LeccionSalon, 'grado' | 'unidad_numero' | 'leccion_numero' | 'leccion_titulo'>) =>
  `${l.grado}.º U${l.unidad_numero} L${l.leccion_numero} · ${l.leccion_titulo}`;
