/**
 * Pantallas del diagnóstico inicial (fase 7a), sobre la misma pantalla del núcleo:
 * - IntroDiagnostico: mensaje amable (con voz) antes de empezar, o "Seguimos donde quedamos".
 * - EntreDiagnostico: entre problemas, neutro: no celebra ni marca errores.
 * - FinDiagnostico: "¡Listo! Ya sé por dónde empezar".
 * - BarraAvance: avance sin conteos (el diagnóstico no tiene un número fijo de problemas).
 */

import { useEffect } from 'react';
import { ArrowRight, Home, Play, Sparkles, Volume2 } from 'lucide-react';
import { useVoz } from '@/hooks/useVoz';

export const TEXTO_INTRO =
  'Antes de empezar, quiero conocerte. Te voy a mostrar algunos problemas. ' +
  'Resuelve como puedas: no importa si no sabes alguno.';
export const TEXTO_RETOMAR = 'Seguimos donde quedamos. Resuelve como puedas: no importa si no sabes alguno.';

function BotonVoz({ texto }: { texto: string }) {
  const voz = useVoz();
  const { callar } = voz;
  useEffect(() => () => callar(), [callar]);
  if (!voz.disponible) return null;
  return (
    <button type="button" onClick={() => voz.hablar(texto)} aria-label="Escuchar" data-testid="boton-voz"
      className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-4 border-primary bg-white text-primary shadow">
      <Volume2 className="h-10 w-10" />
    </button>
  );
}

export function IntroDiagnostico({ retomando, onEmpezar }: { retomando: boolean; onEmpezar: () => void }) {
  const texto = retomando ? TEXTO_RETOMAR : TEXTO_INTRO;
  return (
    <div className="flex flex-col items-center gap-8 py-6 text-center" data-testid="intro-diagnostico">
      <Sparkles className="h-20 w-20 text-primary" />
      <div className="flex items-center gap-4">
        <p className="max-w-2xl text-3xl font-semibold leading-snug text-slate-800">{texto}</p>
        <BotonVoz texto={texto} />
      </div>
      <button type="button" onClick={onEmpezar} autoFocus data-testid="empezar-diagnostico"
        className="flex min-h-[5rem] min-w-[16rem] items-center justify-center gap-3 rounded-3xl bg-primary px-10 text-3xl font-bold text-primary-foreground shadow-lg">
        <Play className="h-9 w-9" /> {retomando ? 'Seguir' : 'Empezar'}
      </button>
    </div>
  );
}

export function EntreDiagnostico({ onSiguiente }: { onSiguiente: () => void }) {
  return (
    <div className="flex flex-col items-center gap-8 py-10 text-center" data-testid="entre-diagnostico">
      <h2 className="text-4xl font-bold text-slate-800">¡Gracias! Vamos con otro.</h2>
      <button type="button" onClick={onSiguiente} autoFocus data-testid="siguiente"
        className="flex min-h-[5rem] min-w-[16rem] items-center justify-center gap-3 rounded-3xl bg-primary px-10 text-3xl font-bold text-primary-foreground shadow-lg">
        Siguiente <ArrowRight className="h-9 w-9" />
      </button>
    </div>
  );
}

export function FinDiagnostico({ onPracticar, onInicio }: { onPracticar: () => void; onInicio: () => void }) {
  return (
    <div className="flex flex-col items-center gap-8 py-8 text-center" data-testid="fin-diagnostico">
      <Sparkles className="h-24 w-24 text-yellow-500 animate-in zoom-in duration-700" />
      <h2 className="text-5xl font-extrabold text-slate-800">¡Listo! Ya sé por dónde empezar.</h2>
      <p className="text-2xl text-slate-600">Gracias por resolver estos problemas.</p>
      <div className="flex flex-wrap justify-center gap-5">
        <button type="button" onClick={onInicio}
          className="flex min-h-[5rem] items-center gap-3 rounded-3xl border-4 border-slate-300 bg-white px-8 text-2xl font-bold">
          <Home className="h-8 w-8" /> Inicio
        </button>
        <button type="button" onClick={onPracticar} autoFocus data-testid="practicar"
          className="flex min-h-[5rem] items-center gap-3 rounded-3xl bg-primary px-8 text-2xl font-bold text-primary-foreground">
          <Play className="h-8 w-8" /> Practicar
        </button>
      </div>
    </div>
  );
}

export function BarraAvance({ avance }: { avance: number }) {
  const pct = Math.round(Math.min(Math.max(avance, 0), 1) * 100);
  return (
    <div className="h-4 w-40 overflow-hidden rounded-full border border-slate-300 bg-slate-200 sm:w-64" role="progressbar"
      aria-label="Avance" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} data-testid="avance-diagnostico">
      <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${Math.max(pct, 4)}%` }} />
    </div>
  );
}
