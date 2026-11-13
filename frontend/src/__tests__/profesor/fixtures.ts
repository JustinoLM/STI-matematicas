import type { LeccionSalon } from '@/types/nucleo';

export function leccion(id: string, extra: Partial<LeccionSalon> = {}): LeccionSalon {
  const [, g, u, l] = /g(\d)-u(\d+)-l(\d+)/.exec(id) ?? ['', '1', '1', '1'];
  return {
    id, grado: Number(g), unidad_numero: Number(u), unidad_titulo: `Unidad ${Number(u)} de ${g}.º`,
    leccion_numero: Number(l), leccion_titulo: `Lección ${id}`,
    orden_programa: Number(g) * 1000 + Number(u) * 10 + Number(l),
    incluida: true, motivo_exclusion: null, parcial: false, nota_parcial: null,
    presentacion_especial: null, cubierta_por: null, caminos: ['naturales.suma'],
    prerrequisitos: [], prerrequisitos_programa: [], prerrequisitos_editados: false,
    tiene_generador: true, habilitada: false, signo: 'siempre', iconos: 'siempre',
    pistas: { 1: true, 2: true, 3: true }, prioritaria: false, ...extra,
  };
}

/** Catálogo pequeño: 1.º U3 (L1 a L3), 1.º U1 excluida, 1.º U4 parcial y dos de 2.º */
export const catalogoBase = (): LeccionSalon[] => [
  leccion('g1-u03-l01', { leccion_titulo: 'Sumemos de forma horizontal', habilitada: true }),
  leccion('g1-u03-l02', { leccion_titulo: 'Restemos de forma horizontal', habilitada: true,
    prerrequisitos: ['g1-u03-l01'], prerrequisitos_programa: ['g1-u03-l01'] }),
  leccion('g1-u03-l03', { leccion_titulo: 'Sumemos y restemos 3 números' }),
  leccion('g1-u01-l01', { leccion_titulo: 'Emparejar objetos', incluida: false, motivo_exclusion: 'prenumérica' }),
  leccion('g1-u04-l03', { leccion_titulo: 'Contemos de forma progresiva', parcial: true, nota_parcial: 'Sin ordinales' }),
  leccion('g2-u03-l01', { leccion_titulo: 'Sumemos llevando', tiene_generador: false, habilitada: true }),
  leccion('g2-u05-l01', { leccion_titulo: 'Decimales de 2.º', cubierta_por: 'sistema_decimales' }),
];
