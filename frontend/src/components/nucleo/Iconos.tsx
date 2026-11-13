/**
 * Íconos de las cantidades del problema, uno por operando, con el objeto del tema narrativo.
 * Hasta 10 van sueltos en filas de 5; desde 11, barras de 10 y unidades sueltas. Si una cantidad
 * del problema pasa de 10, todas se agrupan (10 es una barra) y las barras son compactas.
 * No se dibuja el signo entre los grupos: si el signo está oculto, los íconos no lo revelan.
 */

import { agruparIconos, estiloIconos } from '@/utils/nucleo/iconos';

function BarraDiez({ icono, compacto }: { icono: string; compacto: boolean }) {
  return (
    <span
      className={`inline-flex flex-col items-center border-2 border-amber-500 bg-amber-50 leading-none ${
        compacto ? 'rounded-lg px-0.5 py-0.5' : 'rounded-xl px-1 py-1'}`}
      role="img"
      aria-label="10"
      data-testid="barra-diez"
    >
      {Array.from({ length: 10 }, (_, i) => (
        <span key={i} className={compacto ? 'text-[0.7rem]' : 'text-xl'} aria-hidden>{icono}</span>
      ))}
    </span>
  );
}

interface GrupoProps {
  cantidad: number;
  icono: string;
  umbral: number;
  compacto: boolean;
}

function GrupoCantidad({ cantidad, icono, umbral, compacto }: GrupoProps) {
  const g = agruparIconos(cantidad, umbral);
  return (
    <div className={`flex min-h-[5.5rem] items-center rounded-2xl border-2 border-slate-200 bg-white ${
      compacto ? 'gap-2 px-3 py-2' : 'gap-3 px-4 py-3'}`}
      role="img" aria-label={`${cantidad}`} data-testid="grupo-iconos">
      {g.decenas > 0 && (
        <div className={`flex items-end ${compacto ? 'gap-1' : 'gap-2'}`}>
          {Array.from({ length: g.decenas }, (_, i) => <BarraDiez key={i} icono={icono} compacto={compacto} />)}
        </div>
      )}
      {g.filas.length > 0 && (
        <div className="flex flex-col gap-1">
          {g.filas.map((n, fila) => (
            <div key={fila} className="flex gap-1">
              {Array.from({ length: n }, (_, i) => (
                <span key={i} className={`${compacto ? 'text-xl' : 'text-4xl'} leading-none`} aria-hidden
                  data-testid="icono-suelto">{icono}</span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Iconos({ cantidades, icono }: { cantidades: number[]; icono: string }) {
  const { umbral, compacto } = estiloIconos(cantidades);
  return (
    <div className={`flex flex-wrap items-center justify-center ${compacto ? 'gap-4' : 'gap-8'}`}
      data-testid="iconos" data-compacto={compacto || undefined}>
      {cantidades.map((c, i) => <GrupoCantidad key={i} cantidad={c} icono={icono} umbral={umbral} compacto={compacto} />)}
    </div>
  );
}
