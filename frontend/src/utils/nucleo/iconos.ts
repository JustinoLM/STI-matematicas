/**
 * Íconos de las cantidades (docs/DISENO_MODULAR.md, sección 1 → Presentación).
 *
 * Hasta UMBRAL_DECENAS se dibujan sueltos, en filas de 5 (como un marco de diez, para que se
 * cuenten de un vistazo). Desde ahí se agrupan en decenas: barras de 10 y unidades sueltas.
 * El ícono es el objeto contable del tema narrativo del estudiante.
 */

export const UMBRAL_DECENAS = 10;
/** Por encima de esta cantidad las barras de 10 se dibujan compactas (U5 y U7) */
export const UMBRAL_COMPACTO = UMBRAL_DECENAS;
export const ICONOS_POR_FILA = 5;

export interface GrupoIconos {
  /** Barras de 10 */
  decenas: number;
  /** Unidades sueltas */
  sueltas: number;
  /** Unidades sueltas por fila (filas de ICONOS_POR_FILA) */
  filas: number[];
}

export function agruparIconos(cantidad: number, umbral: number = UMBRAL_DECENAS): GrupoIconos {
  const n = Math.max(0, Math.floor(cantidad));
  const decenas = n > umbral ? Math.floor(n / 10) : 0;
  const sueltas = n - decenas * 10;
  const filas: number[] = [];
  for (let resto = sueltas; resto > 0; resto -= ICONOS_POR_FILA) {
    filas.push(Math.min(ICONOS_POR_FILA, resto));
  }
  return { decenas, sueltas, filas };
}

/** Objeto contable de cada tema narrativo (ids de src/types/shop.ts) */
export const ICONO_POR_TEMA: Record<string, string> = {
  'tema-default': '🍎',
  'tema-piratas': '🪙',
  'tema-astronautas': '⭐',
  'tema-magos': '🔮',
  'tema-caballeros': '🛡️',
  'tema-vaqueros': '🐴',
  'tema-princesas': '💎',
};

export function iconoDelTema(temaId: string | null | undefined): string {
  return (temaId && ICONO_POR_TEMA[temaId]) || ICONO_POR_TEMA['tema-default'];
}

/**
 * Cómo se dibujan los íconos de un problema. Si alguna cantidad pasa del umbral, todas se agrupan
 * en decenas (así 10 + 30 muestra una barra y tres barras, no 10 sueltos junto a barras), y las
 * barras son compactas para que el problema quepa sin desplazarse en la tablet.
 */
export function estiloIconos(cantidades: number[]): { umbral: number; compacto: boolean } {
  const maximo = Math.max(0, ...cantidades);
  return {
    umbral: maximo > UMBRAL_DECENAS ? UMBRAL_DECENAS - 1 : UMBRAL_DECENAS,
    compacto: maximo > UMBRAL_COMPACTO,
  };
}
