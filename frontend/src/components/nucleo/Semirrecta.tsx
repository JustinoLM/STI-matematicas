/**
 * Semirrecta numérica con el punto de partida y los saltos (U5 L5 y U7 L3).
 *
 * Un SVG con viewBox que ocupa el ancho de su columna: se ve igual en tablet (vertical y
 * horizontal) y en computadora. La geometría sale de utils/nucleo/semirrecta.ts. No es
 * interactiva: el estudiante responde con el banco o el teclado.
 *
 * - Resolver: se ven el inicio y los saltos; la llegada no se marca.
 * - Anotar la operación: además se marca la llegada.
 * - En la solución (entre problemas) se marca la llegada.
 */

import type { PresentacionSemirrecta } from '@/types/nucleo';
import { geometriaSemirrecta } from '@/utils/nucleo/semirrecta';

interface SemirrectaProps {
  presentacion: PresentacionSemirrecta;
  /** Quien salta (según el tema) */
  saltarin?: string;
  mostrarLlegada?: boolean;
}

export function Semirrecta({ presentacion, saltarin, mostrarLlegada }: SemirrectaProps) {
  const g = geometriaSemirrecta(presentacion, { mostrarLlegada });
  const tamNumero = 21;
  const yNumero = (abajo: boolean) => g.yLinea + (abajo ? 56 : 30);
  const numero = (valor: number, x: number, clase: string, abajo = false, testid?: string) => (
    <text key={`n${valor}${abajo}`} x={x} y={yNumero(abajo)} textAnchor="middle" fontSize={tamNumero}
      className={clase} data-testid={testid}>
      {valor}
    </text>
  );
  const llegadaExtra = g.numerosExtra.find(n => n.tipo === 'llegada');

  return (
    <figure className="w-full max-w-3xl" data-testid="semirrecta">
      <svg viewBox={`0 0 ${g.ancho} ${g.alto}`} className="h-auto w-full select-none" role="img" aria-label={g.descripcion}>
        <defs>
          <marker id="punta-salto" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-rose-600" />
          </marker>
          <marker id="punta-linea" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" className="fill-slate-500" />
          </marker>
        </defs>

        {/* Línea con flecha a la derecha (la semirrecta sigue) */}
        <line x1={g.x1Linea} y1={g.yLinea} x2={g.x2Linea} y2={g.yLinea} strokeWidth={3}
          className="stroke-slate-500" markerEnd="url(#punta-linea)" />

        {g.marcas.map(m => (
          <line key={m.valor} x1={m.x} x2={m.x} y1={g.yLinea - (m.larga ? 9 : 5)} y2={g.yLinea + (m.larga ? 9 : 5)}
            strokeWidth={m.larga ? 2.5 : 1.5} className="stroke-slate-500" data-testid="marca" />
        ))}

        {/* Llegada resaltada (detrás del número) */}
        {g.llegada && (
          <rect x={g.llegada.x - 20} y={yNumero(!!llegadaExtra?.abajo) - 19} width={40} height={28} rx={8}
            className="fill-orange-200 stroke-orange-500" strokeWidth={2} data-testid="llegada" />
        )}

        {g.marcas.filter(m => m.etiqueta).map(m => numero(m.valor, m.x, 'fill-slate-800 font-semibold'))}
        {g.numerosExtra.map(n => (
          <g key={n.tipo}>
            {n.abajo && <line x1={n.x} x2={n.x} y1={g.yLinea + 10} y2={g.yLinea + 36} strokeWidth={1.5}
              strokeDasharray="3 3" className="stroke-slate-400" />}
            {numero(n.valor, n.x, n.tipo === 'inicio' ? 'fill-rose-700 font-bold' : 'fill-slate-900 font-bold',
              n.abajo, n.tipo === 'inicio' ? 'numero-inicio' : 'numero-llegada')}
          </g>
        ))}

        {/* Saltos */}
        {g.arcos.map((a, i) => {
          const medio = (a.x1 + a.x2) / 2;
          return (
            <g key={i} data-testid="salto">
              <path d={`M ${a.x1} ${g.yLinea - 4} Q ${medio} ${g.yLinea - 4 - 2 * a.alto} ${a.x2} ${g.yLinea - 4}`}
                fill="none" strokeWidth={2.5} className="stroke-rose-600" markerEnd="url(#punta-salto)" />
              {a.conteo && (
                <text x={medio} y={g.yLinea - 10 - a.alto} textAnchor="middle" fontSize={15}
                  className="fill-rose-700 font-semibold">{a.conteo}</text>
              )}
            </g>
          );
        })}

        {/* Punto de partida y quien salta */}
        <circle cx={g.inicio.x} cy={g.yLinea} r={7} className="fill-rose-600" data-testid="inicio" />
        {saltarin && (
          <text x={g.inicio.x} y={g.yLinea - 12 - (g.arcos[0]?.alto ?? 20) - 20} textAnchor="middle" fontSize={30}
            aria-hidden>{saltarin}</text>
        )}
      </svg>
    </figure>
  );
}
