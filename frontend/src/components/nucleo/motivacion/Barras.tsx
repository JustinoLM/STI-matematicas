/**
 * Barras de progreso del núcleo (fase 7b). Nunca se muestran durante la práctica.
 * - BarraNivel: nivel de jugador y experiencia hacia el siguiente.
 * - BarrasCamino: lecciones dominadas sobre el total de cada camino (las "por confirmar" aparte).
 * - CasillasDominio: avance hacia el dominio de una lección. Puede retroceder (regla de "80 % de los
 *   últimos 10"), así que se muestra como casillas con estrellas: un problema sin acierto deja la
 *   casilla vacía, sin rojo ni números que resten, y la meta queda marcada.
 */

import { Star } from 'lucide-react';
import type { ProgresoNucleo } from '@/types/nucleo';

export function BarraNivel({ nivel, enNivel, paraSubir, compacta = false }: {
  nivel: number; enNivel: number; paraSubir: number; compacta?: boolean;
}) {
  const pct = paraSubir ? Math.min(100, Math.round((enNivel / paraSubir) * 100)) : 100;
  return (
    <div className="flex items-center gap-3" data-testid="barra-nivel">
      <div className={`flex shrink-0 flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-amber-300 to-orange-400 font-extrabold text-white shadow ${compacta ? 'h-12 w-12' : 'h-16 w-16'}`}>
        <span className="text-[10px] uppercase leading-none tracking-wide">Nivel</span>
        <span className={compacta ? 'text-xl leading-tight' : 'text-2xl leading-tight'}>{nivel}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="h-4 overflow-hidden rounded-full border border-amber-200 bg-amber-50" role="progressbar"
          aria-label="Experiencia hacia el siguiente nivel" aria-valuemin={0} aria-valuemax={paraSubir} aria-valuenow={enNivel}>
          <div className="h-full rounded-full bg-gradient-to-r from-amber-300 to-orange-400 transition-all duration-700"
            style={{ width: `${Math.max(pct, 3)}%` }} />
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {enNivel} de {paraSubir} de experiencia para el nivel {nivel + 1}
        </p>
      </div>
    </div>
  );
}

export function BarrasCamino({ caminos }: { caminos: ProgresoNucleo['caminos'] }) {
  return (
    <div className="space-y-3" data-testid="barras-camino">
      {caminos.map((c) => {
        const dom = c.total ? (c.dominadas / c.total) * 100 : 0;
        const prov = c.total ? (c.provisionales / c.total) * 100 : 0;
        return (
          <div key={c.camino} data-testid={`barra-camino-${c.camino}`}>
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <span className="font-semibold text-slate-700">{c.nombre}</span>
              <span className="text-sm text-slate-600">
                {c.dominadas} de {c.total} lecciones
                {c.provisionales > 0 && ` · ${c.provisionales} por confirmar`}
              </span>
            </div>
            <div className="flex h-4 overflow-hidden rounded-full bg-slate-100">
              <div className="bg-emerald-500" style={{ width: `${dom}%` }} />
              <div className="bg-sky-300" style={{ width: `${prov}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CasillasDominio({ casillas, aciertos, meta }: { casillas: (boolean | null)[]; aciertos: number; meta: number }) {
  const listo = aciertos >= meta;
  return (
    <div data-testid="casillas-dominio">
      <div className="flex flex-wrap items-center gap-1.5" role="img"
        aria-label={`${aciertos} estrellas en los últimos ${casillas.length} problemas; la meta es ${meta}`}>
        {casillas.map((c, i) => (
          <span key={i} data-testid="casilla" data-estado={c === null ? 'vacia' : c ? 'estrella' : 'sin-estrella'}
            className={`flex h-9 w-9 items-center justify-center rounded-lg border-2 ${
              c ? 'border-amber-300 bg-amber-50' : c === false ? 'border-slate-300 bg-white' : 'border-dashed border-slate-200 bg-slate-50'}`}>
            {c && <Star className="h-6 w-6 fill-amber-400 text-amber-500" />}
          </span>
        ))}
      </div>
      <p className="mt-2 text-sm text-slate-600">
        {listo
          ? `¡${aciertos} estrellas! Practícala otro día para dominarla.`
          : `Llevas ${aciertos} ${aciertos === 1 ? 'estrella' : 'estrellas'} en tus últimos problemas. Meta: ${meta}.`}
      </p>
    </div>
  );
}
