/**
 * Íconos de las cantidades del problema, uno por operando, con el objeto del tema narrativo.
 * Hasta 10 van sueltos en filas de 5; desde 11, barras de 10 y unidades sueltas.
 * No se dibuja el signo entre los grupos: si el signo está oculto, los íconos no lo revelan.
 */

import { agruparIconos } from '@/utils/nucleo/iconos';

function BarraDiez({ icono }: { icono: string }) {
  return (
    <span
      className="inline-flex flex-col items-center rounded-xl border-2 border-amber-500 bg-amber-50 px-1 py-1 leading-none"
      role="img"
      aria-label="10"
      data-testid="barra-diez"
    >
      {Array.from({ length: 10 }, (_, i) => (
        <span key={i} className="text-xl" aria-hidden>{icono}</span>
      ))}
    </span>
  );
}

function GrupoCantidad({ cantidad, icono }: { cantidad: number; icono: string }) {
  const g = agruparIconos(cantidad);
  return (
    <div className="flex min-h-[5.5rem] items-center gap-3 rounded-2xl border-2 border-slate-200 bg-white px-4 py-3"
      role="img" aria-label={`${cantidad}`} data-testid="grupo-iconos">
      {g.decenas > 0 && (
        <div className="flex items-end gap-2">
          {Array.from({ length: g.decenas }, (_, i) => <BarraDiez key={i} icono={icono} />)}
        </div>
      )}
      {g.filas.length > 0 && (
        <div className="flex flex-col gap-1">
          {g.filas.map((n, fila) => (
            <div key={fila} className="flex gap-1">
              {Array.from({ length: n }, (_, i) => (
                <span key={i} className="text-4xl leading-none" aria-hidden data-testid="icono-suelto">{icono}</span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Iconos({ cantidades, icono }: { cantidades: number[]; icono: string }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-8" data-testid="iconos">
      {cantidades.map((c, i) => <GrupoCantidad key={i} cantidad={c} icono={icono} />)}
    </div>
  );
}
