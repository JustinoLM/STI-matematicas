/**
 * Lógica pura del seguimiento del salón (fase 6b): textos de las alertas en lenguaje de docente,
 * agrupación de la tabla por unidad y etiquetas de los estados.
 */

import type { AlertaNucleo, EstadoVisible, FilaAvanceLeccion } from '@/types/nucleo';

export const ESTADOS: EstadoVisible[] = ['dominado', 'repaso', 'por_confirmar', 'en_progreso', 'no_iniciado'];

/** "Por confirmar": el diagnóstico inicial la dio por sabida; la práctica la confirma o la retira. */
export const ETIQUETA_ESTADO: Record<EstadoVisible, string> = {
  dominado: 'Dominan',
  repaso: 'En repaso',
  por_confirmar: 'Por confirmar',
  en_progreso: 'En progreso',
  no_iniciado: 'Sin empezar',
};

/** En singular, para la ficha de un estudiante */
export const ESTADO_UNO: Record<EstadoVisible, string> = {
  dominado: 'Dominada',
  repaso: 'En repaso',
  por_confirmar: 'Por confirmar',
  en_progreso: 'En progreso',
  no_iniciado: 'Sin empezar',
};

/** Clases de color por estado (barra, punto y chip) */
export const COLOR_ESTADO: Record<EstadoVisible, { barra: string; chip: string }> = {
  dominado: { barra: 'bg-emerald-500', chip: 'border-emerald-200 bg-emerald-50 text-emerald-800' },
  repaso: { barra: 'bg-emerald-300', chip: 'border-teal-200 bg-teal-50 text-teal-800' },
  por_confirmar: { barra: 'bg-sky-300', chip: 'border-sky-200 bg-sky-50 text-sky-800' },
  en_progreso: { barra: 'bg-amber-400', chip: 'border-amber-200 bg-amber-50 text-amber-800' },
  no_iniciado: { barra: 'bg-slate-200', chip: 'border-slate-200 bg-slate-50 text-slate-700' },
};

export const porcentaje = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)} %`);

export interface UnidadAvance {
  clave: string;
  titulo: string;
  filas: FilaAvanceLeccion[];
}

/** Las habilitadas agrupadas por unidad (en el orden que llegan) y, al final, las asignadas solo a
 * algunos estudiantes. Con `porMenorDominio`, dentro de cada grupo primero las menos dominadas. */
export function agruparAvance(filas: FilaAvanceLeccion[], porMenorDominio = false): UnidadAvance[] {
  const grupos: UnidadAvance[] = [];
  const asignadas: FilaAvanceLeccion[] = [];
  for (const f of filas) {
    if (!f.habilitada) { asignadas.push(f); continue; }
    const clave = `${f.grado}-${f.unidad_numero}`;
    let g = grupos.find((x) => x.clave === clave);
    if (!g) {
      g = { clave, titulo: `${f.grado}.º · Unidad ${f.unidad_numero} · ${f.unidad_titulo}`, filas: [] };
      grupos.push(g);
    }
    g.filas.push(f);
  }
  if (asignadas.length) grupos.push({ clave: 'asignadas', titulo: 'Asignadas individualmente', filas: asignadas });
  if (porMenorDominio) {
    for (const g of grupos) g.filas = [...g.filas].sort((a, b) => (a.porcentaje_dominan ?? 0) - (b.porcentaje_dominan ?? 0));
  }
  return grupos;
}

/** Identifica una alerta (para saber cuál está guardando una acción) */
export const claveAlerta = (a: AlertaNucleo) => `${a.anio_lectivo_id}-${a.tipo}-${a.estudiante_id}-${a.leccion_id}`;

export interface TextoAlerta {
  titulo: string;
  detalle: string[];
}

/** Título y explicación de una alerta, siempre nombrando estudiante y lección. */
export function textoAlerta(a: AlertaNucleo): TextoAlerta {
  if (a.tipo === 'excelencia') {
    return {
      titulo: `${a.estudiante_nombre} sobresale en «${a.leccion_titulo}»`,
      detalle: [
        `Acertó ${porcentaje(a.precision)} en ${a.problemas} problemas de la zona de extensión, ` +
          'una lección que todavía no está habilitada.',
        'Podrías habilitarla para el salón o asignársela solo a este estudiante.',
      ],
    };
  }
  const detalle = [`Va con ${porcentaje(a.precision)} en sus últimos problemas (${a.problemas} en total).`];
  if (a.motivo === 'refuerzo_insuficiente' && a.prerrequisito_titulo) {
    detalle.push(
      `Ya recibió ${a.refuerzo_recibido} problemas de repaso de «${a.prerrequisito_titulo}» y ahí sigue con ` +
        `${porcentaje(a.precision_prerrequisito)}: el repaso automático no está bastando.`,
    );
    if (a.prerrequisito_asignado) {
      detalle.push(`Ya le asignaste «${a.prerrequisito_titulo}»: le aparecerá en su práctica junto con las del salón.`);
    }
  } else if (a.motivo === 'sin_refuerzo') {
    detalle.push('El sistema no tiene un prerrequisito con ejercicios para darle repaso: conviene apoyarlo en clase.');
  } else if (a.motivo === 'detras_del_salon') {
    detalle.push('Practica la lección pero todavía no la domina, mientras la mayoría del salón ya lo hizo.');
  }
  if (a.total_salon) detalle.push(`${a.dominan_salon} de ${a.total_salon} compañeros ya la dominan.`);
  return { titulo: `${a.estudiante_nombre} tiene dificultad con «${a.leccion_titulo}»`, detalle };
}
