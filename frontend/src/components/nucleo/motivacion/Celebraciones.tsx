/**
 * Celebraciones del núcleo (fase 7b): lección dominada, lección recuperada tras un repaso, medalla
 * nueva y subida de nivel. Solo entre problemas y al final de la sesión; nunca durante el problema.
 */

import { RotateCcw, Sparkles, Star } from 'lucide-react';
import type { Celebracion } from '@/types/nucleo';
import { DibujoMedalla } from './Medalla';
import { textoCelebracion } from './textos';

export function ListaCelebraciones({ celebraciones, grande = true }: { celebraciones: Celebracion[]; grande?: boolean }) {
  if (celebraciones.length === 0) return null;
  return (
    <ul className="flex flex-col items-center gap-3" data-testid="celebraciones">
      {celebraciones.map((c, i) => (
        <li key={i} data-testid={`celebracion-${c.tipo}`}
          className={`flex items-center gap-3 rounded-3xl bg-white/90 px-5 py-3 font-bold shadow animate-in zoom-in duration-500 ${grande ? 'text-2xl' : 'text-lg'}`}>
          {c.tipo === 'medalla' ? <DibujoMedalla medalla={{ ...c.medalla, obtenida: true }} tamano={grande ? 48 : 36} />
            : c.tipo === 'nivel' ? <Sparkles className="h-9 w-9 text-orange-500" />
            : c.tipo === 'leccion_recuperada' ? <RotateCcw className="h-9 w-9 text-emerald-600" />
            : <Star className="h-9 w-9 fill-amber-400 text-amber-500" />}
          <span className="text-slate-800">{textoCelebracion(c)}</span>
        </li>
      ))}
    </ul>
  );
}
