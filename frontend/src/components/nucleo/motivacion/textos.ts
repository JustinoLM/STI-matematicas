/**
 * Textos de la motivación del núcleo (fase 7b), aparte de los componentes para que la recarga
 * en caliente de Vite siga funcionando.
 */

import type { Celebracion, EstadoParada } from '@/types/nucleo';

export const NOMBRE_GRADO: Record<string, string> = { bronce: 'Bronce', plata: 'Plata', oro: 'Oro' };

export const TEXTO_ESTADO: Record<EstadoParada, string> = {
  dominado: 'Dominada',
  repaso: 'Dominada (toca repasarla)',
  provisional: 'Por confirmar',
  en_progreso: 'En práctica',
  no_iniciado: 'Por descubrir',
};

export function textoCelebracion(c: Celebracion): string {
  switch (c.tipo) {
    case 'leccion_dominada': return `¡Dominaste «${c.titulo}»!`;
    case 'leccion_recuperada': return `¡La recuperaste! «${c.titulo}» vuelve a estar dominada.`;
    case 'medalla': {
      const grado = NOMBRE_GRADO[c.medalla.grado_medalla];
      return `¡Medalla nueva! ${c.medalla.titulo}${grado ? ` · ${grado}` : ''}`;
    }
    case 'nivel': return `¡Subiste al nivel ${c.nivel}!`;
  }
}
