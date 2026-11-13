/**
 * Pantalla entre problemas: aquí sí van las celebraciones (docs/DISENO_MODULAR.md, sección 3 →
 * Motivación). Si acertó: felicitación, experiencia ganada y el efecto de victoria del
 * estudiante, si tiene uno activo. Si agotó los intentos: la solución, sin castigo.
 */

import { useState } from 'react';
import { ArrowRight, Star } from 'lucide-react';
import { VictoryEffect, type AnimationType } from '@/components/practice/VictoryEffect';
import { useThemeStore } from '@/store/themeStore';
import { EFECTOS } from '@/types/shop';
import type { Problema, ResultadoRespuesta } from '@/types/nucleo';
import { vocabularioDelTema } from '@/utils/nucleo/plantillas';
import { respuestasDesdeSolucion } from '@/utils/nucleo/respuestas';
import { Expresion } from './Expresion';
import { Semirrecta } from './Semirrecta';

/** Solución de la semirrecta de leer (el número) o de ubicar (la letra de la flecha) */
function respuestaSemirrecta(solucion: Record<string, unknown> | null): { valor?: number; etiqueta?: string } {
  if (!solucion) return {};
  if (typeof solucion.flecha === 'string') return { etiqueta: solucion.flecha };
  if (typeof solucion.resultado === 'string') return { valor: Number(solucion.resultado) };
  return {};
}

interface EntreProblemasProps {
  resultado: ResultadoRespuesta;
  problema: Problema;
  onSiguiente: () => void;
}

export function EntreProblemas({ resultado, problema, onSiguiente }: EntreProblemasProps) {
  const { efectoActivoId, efectosSonidoActivados, volumen, temaActivoId } = useThemeStore.getState();
  const efecto = resultado.correcto && efectoActivoId ? EFECTOS.find(e => e.id === efectoActivoId) : undefined;
  const [mostrarEfecto, setMostrarEfecto] = useState(!!efecto?.config?.animacion);

  return (
    <div className="flex flex-col items-center gap-8 py-6 text-center" data-testid="entre-problemas">
      {resultado.correcto ? (
        <>
          <div className="flex gap-3 text-yellow-400 animate-in zoom-in duration-500">
            {[0, 1, 2].map(i => <Star key={i} className="h-20 w-20 fill-current" />)}
          </div>
          <h2 className="text-5xl font-extrabold text-green-700">¡Muy bien!</h2>
          {resultado.evento_dominio === 'dominada' && (
            <p className="text-3xl font-bold text-primary">¡Ya dominas esta lección!</p>
          )}
          {resultado.experiencia_ganada > 0 && (
            <p className="text-2xl font-semibold text-slate-700">+{resultado.experiencia_ganada} de experiencia</p>
          )}
        </>
      ) : (
        <>
          <h2 className="text-4xl font-bold text-slate-800">Así se resuelve:</h2>
          {problema.forma === 'expresion' && problema.presentacion?.tipo === 'semirrecta' && (
            <Semirrecta presentacion={problema.presentacion} mostrarLlegada
              respuesta={respuestaSemirrecta(resultado.solucion)}
              saltarin={vocabularioDelTema(temaActivoId).saltarin} />
          )}
          {problema.forma === 'expresion' && resultado.solucion ? (
            <Expresion problema={problema} respuestas={respuestasDesdeSolucion(problema, resultado.solucion)} soloLectura />
          ) : problema.forma === 'ordenar' && Array.isArray(resultado.solucion?.orden) ? (
            <p className="text-5xl font-bold tracking-wide">{(resultado.solucion!.orden as string[]).join('  ')}</p>
          ) : null}
          <p className="text-2xl text-slate-600">¡Sigue practicando, lo vas a lograr!</p>
        </>
      )}

      <button
        type="button"
        onClick={onSiguiente}
        autoFocus
        data-testid="siguiente"
        className="flex min-h-[5rem] min-w-[16rem] items-center justify-center gap-3 rounded-3xl bg-primary px-10 text-3xl font-bold text-primary-foreground shadow-lg"
      >
        {resultado.sesion_completada ? 'Ver resultados' : 'Siguiente'}
        <ArrowRight className="h-9 w-9" />
      </button>

      {mostrarEfecto && efecto?.config?.animacion && (
        <VictoryEffect
          animacion={efecto.config.animacion as AnimationType}
          duracionMs={efecto.config.duracionMs ?? 2000}
          sonido={efectosSonidoActivados ? efecto.config.sonido : undefined}
          audioVolumen={efectosSonidoActivados ? volumen : 0}
          onDone={() => setMostrarEfecto(false)}
        />
      )}
    </div>
  );
}
