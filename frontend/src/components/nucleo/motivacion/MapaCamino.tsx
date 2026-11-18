/**
 * Mapa del camino (fase 7b). Cada unidad del grado es un tramo y cada lección una parada:
 * - dominada: encendida (color del tema, con estrella); en repaso, también encendida;
 * - "por confirmar" (dominio provisional del diagnóstico): borde punteado celeste, sin estrella;
 * - la siguiente: grande, con "¡Vas aquí!";
 * - en progreso: normal; las demás, tenues.
 * Las decoraciones son dibujos SVG propios según el tema narrativo activo.
 * El tramo usa porcentajes de ancho y alto fijo por parada: funciona en tablet vertical y horizontal.
 */

import type { ReactNode } from 'react';
import { Check, Star } from 'lucide-react';
import type { ParadaMapa, ProgresoNucleo } from '@/types/nucleo';
import { TEXTO_ESTADO } from './textos';

interface EstiloTema {
  fondo: string;          // clases del fondo del tramo
  acento: string;         // color de las paradas encendidas
  camino: string;         // color del trazo
  titulo: string;         // nombre del camino según el tema
  adornos: ((p: { x: number; y: number }) => ReactNode)[];
}

// ─── Adornos (SVG propios, en coordenadas del tramo: x de 0 a 100, y en px) ───

const ola = ({ x, y }: { x: number; y: number }) => (
  <path d={`M${x - 6} ${y} q3 -4 6 0 t6 0`} fill="none" stroke="#38bdf8" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
);
const islita = ({ x, y }: { x: number; y: number }) => (
  <g><ellipse cx={x} cy={y + 6} rx="7" ry="3" fill="#fde68a" /><path d={`M${x} ${y + 5} v-12`} stroke="#92400e" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    <path d={`M${x} ${y - 7} l-5 3 M${x} ${y - 7} l5 3 M${x} ${y - 7} l-3 -3 M${x} ${y - 7} l3 -3`} stroke="#16a34a" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></g>
);
const planeta = ({ x, y }: { x: number; y: number }) => (
  <g><circle cx={x} cy={y} r="5" fill="#a78bfa" /><ellipse cx={x} cy={y} rx="9" ry="2" fill="none" stroke="#fbbf24" strokeWidth="1.2" vectorEffect="non-scaling-stroke" /></g>
);
const estrellita = ({ x, y }: { x: number; y: number }) => (
  <path d={`M${x} ${y - 4} l1.2 2.8 3 .3 -2.3 2 .7 3 -2.6 -1.6 -2.6 1.6 .7 -3 -2.3 -2 3 -.3z`} fill="#fde047" />
);
const chispa = ({ x, y }: { x: number; y: number }) => (
  <path d={`M${x} ${y - 5} v10 M${x - 5} ${y} h10 M${x - 3} ${y - 3} l6 6 M${x + 3} ${y - 3} l-6 6`} stroke="#c084fc" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
);
const sombrero = ({ x, y }: { x: number; y: number }) => (
  <g><path d={`M${x - 4} ${y} l2 -7 h4 l2 7z`} fill="#7c3aed" /><circle cx={x} cy={y - 7} r="1" fill="#fde047" /></g>
);
const torre = ({ x, y }: { x: number; y: number }) => (
  <g fill="#94a3b8"><rect x={x - 3} y={y - 8} width="6" height="12" /><path d={`M${x - 4} ${y - 8} h8 l-4 -5z`} fill="#ef4444" /></g>
);
const banderin = ({ x, y }: { x: number; y: number }) => (
  <g><path d={`M${x} ${y + 5} v-12`} stroke="#57534e" strokeWidth="1.2" vectorEffect="non-scaling-stroke" /><path d={`M${x} ${y - 7} l6 2 -6 2z`} fill="#2563eb" /></g>
);
const cactus = ({ x, y }: { x: number; y: number }) => (
  <g fill="#16a34a"><rect x={x - 1.5} y={y - 8} width="3" height="13" rx="1.5" /><rect x={x - 5} y={y - 4} width="2.5" height="5" rx="1.2" /><rect x={x + 2.5} y={y - 6} width="2.5" height="5" rx="1.2" /></g>
);
const sol = ({ x, y }: { x: number; y: number }) => (
  <circle cx={x} cy={y} r="4" fill="#fb923c" opacity="0.8" />
);
const engrane = ({ x, y }: { x: number; y: number }) => (
  <g><circle cx={x} cy={y} r="4.5" fill="none" stroke="#db2777" strokeWidth="2.5" strokeDasharray="2 1.5" vectorEffect="non-scaling-stroke" /><circle cx={x} cy={y} r="1.5" fill="#db2777" /></g>
);
const corona = ({ x, y }: { x: number; y: number }) => (
  <path d={`M${x - 5} ${y + 2} l1 -6 2.5 3 1.5 -4 1.5 4 2.5 -3 1 6z`} fill="#f59e0b" />
);
const arbol = ({ x, y }: { x: number; y: number }) => (
  <g><rect x={x - 0.8} y={y} width="1.6" height="5" fill="#92400e" /><circle cx={x} cy={y - 2} r="4.5" fill="#4ade80" /></g>
);
const nube = ({ x, y }: { x: number; y: number }) => (
  <g fill="#e2e8f0"><circle cx={x - 3} cy={y} r="3" /><circle cx={x + 1} cy={y - 1.5} r="4" /><circle cx={x + 4.5} cy={y + 0.5} r="2.5" /></g>
);

const TEMAS: Record<string, EstiloTema> = {
  'tema-piratas': { fondo: 'bg-gradient-to-b from-sky-50 to-cyan-100', acento: 'bg-amber-500', camino: '#0ea5e9', titulo: 'La ruta del tesoro', adornos: [ola, islita, ola] },
  'tema-astronautas': { fondo: 'bg-gradient-to-b from-indigo-950 to-slate-800', acento: 'bg-violet-500', camino: '#a5b4fc', titulo: 'Viaje por las estrellas', adornos: [estrellita, planeta, estrellita] },
  'tema-magos': { fondo: 'bg-gradient-to-b from-purple-50 to-fuchsia-100', acento: 'bg-purple-600', camino: '#a855f7', titulo: 'El sendero mágico', adornos: [chispa, sombrero, chispa] },
  'tema-caballeros': { fondo: 'bg-gradient-to-b from-stone-50 to-emerald-50', acento: 'bg-blue-600', camino: '#78716c', titulo: 'El camino del reino', adornos: [banderin, torre, banderin] },
  'tema-vaqueros': { fondo: 'bg-gradient-to-b from-amber-50 to-orange-100', acento: 'bg-orange-600', camino: '#b45309', titulo: 'La ruta del desierto', adornos: [cactus, sol, cactus] },
  'tema-princesas': { fondo: 'bg-gradient-to-b from-pink-50 to-rose-100', acento: 'bg-pink-600', camino: '#ec4899', titulo: 'El taller de inventos', adornos: [engrane, corona, engrane] },
  'tema-default': { fondo: 'bg-gradient-to-b from-emerald-50 to-sky-50', acento: 'bg-emerald-500', camino: '#10b981', titulo: 'Mi camino', adornos: [arbol, nube, arbol] },
};

function estiloTema(temaId: string | null | undefined): EstiloTema {
  return TEMAS[temaId ?? ''] ?? TEMAS['tema-default'];
}

const ALTO_PARADA = 104;          // px por parada
const XS = [28, 50, 72, 50];      // zigzag en % del ancho

function Parada({ parada, estilo, onElegir, elegida }: {
  parada: ParadaMapa; estilo: EstiloTema; onElegir: (p: ParadaMapa) => void; elegida: boolean;
}) {
  const encendida = parada.estado === 'dominado' || parada.estado === 'repaso';
  const provisional = parada.estado === 'provisional';
  const tenue = !encendida && !provisional && !parada.siguiente && parada.estado !== 'en_progreso';
  const tamano = parada.siguiente ? 'h-20 w-20 text-3xl' : 'h-16 w-16 text-2xl';
  const clases = encendida
    ? `${estilo.acento} text-white border-white shadow-lg`
    : provisional
      ? 'bg-white text-sky-700 border-dashed border-sky-400'
      : parada.siguiente
        ? 'bg-white text-slate-800 border-amber-400 shadow-xl ring-8 ring-amber-200'
        : 'bg-white text-slate-700 border-slate-300';
  return (
    <button type="button" onClick={() => onElegir(parada)}
      aria-label={`Lección ${parada.leccion_numero}: ${parada.titulo}. ${TEXTO_ESTADO[parada.estado]}`}
      aria-pressed={elegida}
      data-testid={`parada-${parada.leccion_id}`} data-estado={parada.estado} data-siguiente={parada.siguiente}
      className={`relative flex items-center justify-center rounded-full border-4 font-extrabold transition ${tamano} ${clases} ${tenue ? 'opacity-40' : ''} ${elegida ? 'outline outline-4 outline-offset-2 outline-slate-400' : ''}`}>
      {parada.leccion_numero}
      {encendida && <Star className="absolute -right-1 -top-1 h-7 w-7 fill-amber-300 text-amber-500" />}
      {provisional && <span className="absolute -right-1 -top-1 rounded-full bg-sky-100 px-1 text-xs text-sky-700">?</span>}
      {parada.siguiente && (
        <span className="absolute -bottom-7 whitespace-nowrap rounded-full bg-amber-400 px-2 py-0.5 text-xs font-bold text-white">¡Vas aquí!</span>
      )}
      {parada.estado === 'repaso' && <Check className="absolute -bottom-1 -left-1 h-5 w-5 rounded-full bg-white text-emerald-600" />}
    </button>
  );
}

export function MapaCamino({ unidades, temaId, elegida, onElegir, grado }: {
  unidades: ProgresoNucleo['unidades']; temaId: string | null | undefined; grado: number | null;
  elegida: string | null; onElegir: (p: ParadaMapa) => void;
}) {
  const estilo = estiloTema(temaId);
  const oscuro = temaId === 'tema-astronautas';
  return (
    <div className={`rounded-[2rem] p-4 ${estilo.fondo}`} data-testid="mapa-camino" data-tema={temaId ?? 'tema-default'}>
      <h2 className={`mb-2 text-center text-2xl font-extrabold ${oscuro ? 'text-white' : 'text-slate-800'}`}>
        {estilo.titulo}{grado ? ` · ${grado}.º` : ''}
      </h2>
      {unidades.map((u) => {
        const alto = u.lecciones.length * ALTO_PARADA + 24;
        const puntos = u.lecciones.map((_, i) => ({ x: XS[i % XS.length], y: i * ALTO_PARADA + ALTO_PARADA / 2 }));
        const trazo = puntos.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x} ${p.y}`).join(' ');
        return (
          <section key={u.unidad_numero} className="mt-4" aria-label={`Unidad ${u.unidad_numero}: ${u.titulo}`}>
            <p className={`mx-auto w-fit rounded-full px-4 py-1 text-center text-sm font-bold ${oscuro ? 'bg-white/15 text-white' : 'bg-white/80 text-slate-700'}`}>
              Unidad {u.unidad_numero} · {u.titulo}
            </p>
            <div className="relative mx-auto max-w-xl" style={{ height: alto }}>
              <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 100 ${alto}`} preserveAspectRatio="none" aria-hidden="true">
                <path d={trazo} fill="none" stroke={estilo.camino} strokeWidth="6" strokeLinecap="round" strokeDasharray="1 14"
                  vectorEffect="non-scaling-stroke" opacity="0.7" />
              </svg>
              {puntos.map((p, i) => {
                const adorno = estilo.adornos[i % estilo.adornos.length];
                // Al lado contrario de la parada, en su propio SVG para que no se deforme
                const x = p.x > 50 ? 12 : p.x < 50 ? 88 : (i % 2 ? 12 : 88);
                return (
                  <svg key={i} viewBox="0 0 24 24" width="56" height="56" aria-hidden="true" data-testid="adorno"
                    className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${x}%`, top: p.y }}>
                    {adorno({ x: 12, y: 12 })}
                  </svg>
                );
              })}
              {u.lecciones.map((parada, i) => (
                <div key={parada.leccion_id} className="absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${puntos[i].x}%`, top: puntos[i].y }}>
                  <Parada parada={parada} estilo={estilo} onElegir={onElegir} elegida={elegida === parada.leccion_id} />
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

