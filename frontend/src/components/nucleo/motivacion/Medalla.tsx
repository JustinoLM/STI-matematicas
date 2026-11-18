/**
 * Medallas del núcleo dibujadas con SVG propio (fase 7b): cinta y disco con un símbolo.
 * - Lección dominada: disco azul con estrella.
 * - Unidad completa: disco morado con un escudo.
 * - Hito del camino: bronce, plata u oro con una bandera.
 * Una medalla por ganar se ve en gris con su avance (por ejemplo "2 de 4").
 */

import type { MedallaNucleo } from '@/types/nucleo';
import { NOMBRE_GRADO } from './textos';

const COLORES: Record<string, { disco: string; borde: string; cinta: string }> = {
  leccion: { disco: '#60a5fa', borde: '#2563eb', cinta: '#93c5fd' },
  unidad: { disco: '#a78bfa', borde: '#7c3aed', cinta: '#c4b5fd' },
  bronce: { disco: '#d6a26b', borde: '#9a5b25', cinta: '#f0c9a0' },
  plata: { disco: '#cbd5e1', borde: '#64748b', cinta: '#e2e8f0' },
  oro: { disco: '#facc15', borde: '#ca8a04', cinta: '#fde68a' },
  gris: { disco: '#e2e8f0', borde: '#cbd5e1', cinta: '#f1f5f9' },
};

function Simbolo({ tipo, color }: { tipo: string; color: string }) {
  if (tipo === 'leccion') {
    return <path d="M32 22 l3.5 7.2 7.9 1.1 -5.7 5.6 1.3 7.9 -7-3.7 -7 3.7 1.3-7.9 -5.7-5.6 7.9-1.1z" fill={color} />;
  }
  if (tipo === 'unidad') {
    return <path d="M32 21 l10 4 v7 c0 7 -4.5 11 -10 13 c-5.5-2 -10-6 -10-13 v-7z" fill={color} />;
  }
  return (
    <g fill={color}>
      <rect x="24" y="21" width="2.6" height="24" rx="1" />
      <path d="M26.6 22 h15 l-4 5 4 5 h-15z" />
    </g>
  );
}

export function DibujoMedalla({ medalla, tamano = 64 }: { medalla: Pick<MedallaNucleo, 'tipo' | 'grado_medalla' | 'obtenida'>; tamano?: number }) {
  const clave = !medalla.obtenida ? 'gris' : medalla.tipo === 'camino' ? medalla.grado_medalla : medalla.tipo;
  const c = COLORES[clave] ?? COLORES.gris;
  return (
    <svg viewBox="0 0 64 76" width={tamano} height={(tamano * 76) / 64} aria-hidden="true">
      <path d="M20 2 h10 l4 14 h-10z" fill={c.cinta} />
      <path d="M34 2 h10 l-4 14 h-10z" fill={c.cinta} opacity="0.85" />
      <circle cx="32" cy="44" r="24" fill={c.disco} stroke={c.borde} strokeWidth="4" />
      <circle cx="32" cy="44" r="17" fill="none" stroke="white" strokeOpacity="0.45" strokeWidth="2" />
      <g transform="translate(0 11)">
        <Simbolo tipo={medalla.tipo} color={medalla.obtenida ? 'white' : '#94a3b8'} />
      </g>
    </svg>
  );
}

export function TarjetaMedalla({ medalla }: { medalla: MedallaNucleo }) {
  const grado = NOMBRE_GRADO[medalla.grado_medalla];
  return (
    <div data-testid={`medalla-${medalla.tipo}-${medalla.clave}${medalla.grado_medalla ? `-${medalla.grado_medalla}` : ''}`}
      data-obtenida={medalla.obtenida}
      className={`flex flex-col items-center gap-1 rounded-2xl border p-3 text-center ${medalla.obtenida ? 'bg-white' : 'bg-slate-50'}`}>
      <DibujoMedalla medalla={medalla} />
      <p className={`text-sm font-semibold leading-tight ${medalla.obtenida ? 'text-slate-800' : 'text-slate-500'}`}>
        {medalla.titulo}{grado ? ` · ${grado}` : ''}
      </p>
      <p className="text-xs text-slate-500">
        {medalla.obtenida ? medalla.descripcion : `${medalla.logradas} de ${medalla.meta}`}
      </p>
    </div>
  );
}
