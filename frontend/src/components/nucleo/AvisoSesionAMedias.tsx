/**
 * Aviso de práctica a medias del núcleo: continuar donde la dejó o descartarla y empezar otra.
 * Se usa en el dashboard y al entrar a la pantalla de práctica.
 */

import { Play, Trash2 } from 'lucide-react';
import type { SesionActivaNucleo } from '@/types/nucleo';

interface AvisoProps {
  sesion: SesionActivaNucleo;
  onContinuar: () => void;
  onDescartar: () => void;
  ocupado?: boolean;
  /** Texto del botón de descartar: "Descartar" en el dashboard, "Empezar de nuevo" en la práctica */
  textoDescartar?: string;
}

function hace(min: number): string {
  if (min < 1) return 'hace un momento';
  if (min < 60) return `hace ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return h === 1 ? 'hace 1 hora' : `hace ${h} horas`;
  const d = Math.floor(h / 24);
  return d === 1 ? 'ayer' : `hace ${d} días`;
}

export function AvisoSesionAMedias({ sesion, onContinuar, onDescartar, ocupado, textoDescartar = 'Descartar' }: AvisoProps) {
  return (
    <div className="rounded-3xl border-4 border-amber-300 bg-amber-50 p-6" data-testid="aviso-sesion">
      <p className="text-2xl font-bold text-amber-900">Tienes una práctica a medias</p>
      <p className="mt-1 text-lg text-amber-800">
        Hiciste {sesion.progreso} de {sesion.cantidad_problemas} problemas ({hace(sesion.minutos_transcurridos)}).
      </p>
      <div className="mt-5 flex flex-wrap gap-4">
        <button type="button" onClick={onContinuar} disabled={ocupado} data-testid="continuar"
          className="flex min-h-[4.5rem] items-center gap-3 rounded-2xl bg-green-600 px-8 text-2xl font-bold text-white disabled:opacity-50">
          <Play className="h-8 w-8" /> Continuar
        </button>
        <button type="button" onClick={onDescartar} disabled={ocupado} data-testid="descartar"
          className="flex min-h-[4.5rem] items-center gap-3 rounded-2xl border-2 border-slate-300 bg-white px-6 text-xl font-semibold text-slate-700 disabled:opacity-50">
          <Trash2 className="h-7 w-7" /> {textoDescartar}
        </button>
      </div>
    </div>
  );
}
