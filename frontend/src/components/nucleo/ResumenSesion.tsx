/**
 * Final de la sesión del núcleo: celebración, problemas resueltos y experiencia ganada.
 */

import { Home, RotateCcw, Trophy } from 'lucide-react';

export interface ResultadoProblema {
  correcto: boolean;
  experiencia: number;
}

interface ResumenSesionProps {
  resultados: ResultadoProblema[];
  onInicio: () => void;
  onOtra: () => void;
}

export function ResumenSesion({ resultados, onInicio, onOtra }: ResumenSesionProps) {
  const bien = resultados.filter(r => r.correcto).length;
  const experiencia = resultados.reduce((s, r) => s + r.experiencia, 0);
  return (
    <div className="flex flex-col items-center gap-8 py-8 text-center" data-testid="resumen">
      <Trophy className="h-28 w-28 text-yellow-500 animate-in zoom-in duration-700" />
      <h2 className="text-5xl font-extrabold text-slate-800">¡Terminaste la práctica!</h2>
      {resultados.length > 0 && (
        <p className="text-3xl font-semibold text-slate-700">
          Resolviste {bien} de {resultados.length} problemas
        </p>
      )}
      {experiencia > 0 && <p className="text-2xl text-primary">+{experiencia} de experiencia</p>}
      <div className="flex flex-wrap justify-center gap-5">
        <button type="button" onClick={onInicio}
          className="flex min-h-[5rem] items-center gap-3 rounded-3xl border-4 border-slate-300 bg-white px-8 text-2xl font-bold">
          <Home className="h-8 w-8" /> Inicio
        </button>
        <button type="button" onClick={onOtra}
          className="flex min-h-[5rem] items-center gap-3 rounded-3xl bg-primary px-8 text-2xl font-bold text-primary-foreground">
          <RotateCcw className="h-8 w-8" /> Practicar otra vez
        </button>
      </div>
    </div>
  );
}
