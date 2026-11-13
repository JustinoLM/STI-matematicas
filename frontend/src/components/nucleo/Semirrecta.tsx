/**
 * Semirrecta numérica: con el punto de partida y los saltos (U5 L5 y U7 L3), o con flechas que
 * señalan números (U4 L2 y U6 L4: leer el número de una flecha, o elegir la flecha de un número).
 *
 * Un SVG con viewBox que ocupa el ancho de su columna: se ve igual en tablet (vertical y
 * horizontal) y en computadora. La geometría sale de utils/nucleo/semirrecta.ts. No es
 * interactiva: el estudiante responde con el banco o el teclado.
 *
 * - Resolver: se ven el inicio y los saltos; la llegada no se marca.
 * - Anotar la operación: además se marca la llegada.
 * - En la solución (entre problemas) se marca la llegada.
 * - Leer: una flecha (con el personaje del tema encima) señala una marca sin número.
 * - Ubicar: tres flechas con las letras A, B y C; el estudiante arrastra la letra.
 * - En la solución de leer y ubicar se escribe el número señalado y se resalta su flecha.
 */

import type { PresentacionSemirrecta, PresentacionSemirrectaPuntos } from '@/types/nucleo';
import { esSemirrectaDePuntos, geometriaPuntos, geometriaSemirrecta } from '@/utils/nucleo/semirrecta';

interface SemirrectaProps {
  presentacion: PresentacionSemirrecta | PresentacionSemirrectaPuntos;
  /** Quien salta, o quien señala en "leer" (según el tema) */
  saltarin?: string;
  mostrarLlegada?: boolean;
  /** Solución de leer o ubicar: el número señalado (leer) o la letra correcta (ubicar) */
  respuesta?: { valor?: number; etiqueta?: string };
}

const NUMERO = 21;

/** El alto de la semirrecta sale de su ancho (viewBox de 640 × 165). En una pantalla baja (tablet
 * horizontal) se limita el ancho para que quepa debajo de las dos columnas sin desplazarse. */
const ESTILO_FIGURA = { maxWidth: 'min(48rem, max(24rem, calc((100vh - 610px) * 640 / 165)))' } as const;

function PuntosSemirrecta({ presentacion, saltarin, respuesta }: Omit<SemirrectaProps, 'mostrarLlegada'> & {
  presentacion: PresentacionSemirrectaPuntos;
}) {
  const g = geometriaPuntos(presentacion);
  const yNumero = g.yLinea + 30;
  const leer = presentacion.ejercicio === 'leer';
  return (
    <figure className="w-full max-w-3xl" style={ESTILO_FIGURA} data-testid="semirrecta" data-ejercicio={presentacion.ejercicio}>
      <svg viewBox={`0 0 ${g.ancho} ${g.alto}`} className="h-auto w-full select-none" role="img" aria-label={g.descripcion}>
        <defs>
          <marker id="punta-linea" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" className="fill-slate-500" />
          </marker>
          <marker id="punta-flecha" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" className="fill-rose-600" />
          </marker>
        </defs>
        <line x1={g.x1Linea} y1={g.yLinea} x2={g.x2Linea} y2={g.yLinea} strokeWidth={3}
          className="stroke-slate-500" markerEnd="url(#punta-linea)" />
        {g.marcas.map(m => (
          <line key={m.valor} x1={m.x} x2={m.x} y1={g.yLinea - (m.larga ? 9 : 5)} y2={g.yLinea + (m.larga ? 9 : 5)}
            strokeWidth={m.larga ? 2.5 : 1.5} className="stroke-slate-500" data-testid="marca" />
        ))}
        {g.marcas.filter(m => m.etiqueta).map(m => (
          <text key={`n${m.valor}`} x={m.x} y={yNumero} textAnchor="middle" fontSize={NUMERO}
            className="fill-slate-800 font-semibold">{m.valor}</text>
        ))}
        {/* Números sin escribir: recuadros; el señalado lleva "?" (o la respuesta en la solución) */}
        {g.casillas.map(c => (
          <g key={`c${c.valor}`} data-testid="casilla-oculta">
            <rect x={c.x - g.anchoCasilla / 2} y={yNumero - 20} width={g.anchoCasilla} height={27} rx={6}
              strokeWidth={2} strokeDasharray={c.senalada ? undefined : '4 3'}
              className={c.senalada ? 'fill-orange-100 stroke-orange-500' : 'fill-white stroke-slate-400'} />
            {c.senalada && (
              <text x={c.x} y={yNumero} textAnchor="middle" fontSize={NUMERO - 3} className="fill-slate-900 font-bold">
                {respuesta?.valor ?? '?'}
              </text>
            )}
          </g>
        ))}
        {/* Flechas hacia abajo, hasta la marca */}
        {g.flechas.map(f => {
          const correcta = respuesta?.etiqueta !== undefined && respuesta.etiqueta === f.etiqueta;
          return (
            <g key={`f${f.valor}`} data-testid="flecha" data-etiqueta={f.etiqueta ?? undefined}>
              <line x1={f.x} x2={f.x} y1={g.yLinea - 58} y2={g.yLinea - 12} strokeWidth={3}
                className="stroke-rose-600" markerEnd="url(#punta-flecha)" />
              {f.etiqueta && (
                <g>
                  <circle cx={f.x} cy={g.yLinea - 76} r={17} strokeWidth={correcta ? 4 : 2}
                    className={correcta ? 'fill-green-100 stroke-green-600' : 'fill-white stroke-rose-600'} />
                  <text x={f.x} y={g.yLinea - 69} textAnchor="middle" fontSize={21} className="fill-rose-700 font-bold">
                    {f.etiqueta}
                  </text>
                </g>
              )}
              {leer && saltarin && (
                <text x={f.x} y={g.yLinea - 64} textAnchor="middle" fontSize={30} aria-hidden>{saltarin}</text>
              )}
              {/* Solución: el número señalado, si no tiene ya número ni recuadro */}
              {respuesta && (leer ? respuesta.valor !== undefined : correcta)
                && !g.casillas.some(c => c.valor === f.valor) && (
                <g data-testid="numero-senalado">
                  <rect x={f.x - 22} y={yNumero + 6} width={44} height={28} rx={8} strokeWidth={2}
                    className="fill-orange-200 stroke-orange-500" />
                  <text x={f.x} y={yNumero + 27} textAnchor="middle" fontSize={NUMERO} className="fill-slate-900 font-bold">
                    {f.valor}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export function Semirrecta({ presentacion, saltarin, mostrarLlegada, respuesta }: SemirrectaProps) {
  if (esSemirrectaDePuntos(presentacion)) {
    return <PuntosSemirrecta presentacion={presentacion} saltarin={saltarin} respuesta={respuesta} />;
  }
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
    <figure className="w-full max-w-3xl" style={ESTILO_FIGURA} data-testid="semirrecta">
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
