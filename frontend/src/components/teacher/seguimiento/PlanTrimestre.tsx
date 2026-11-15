/**
 * Plan por trimestre (fase 6b, opcional). El profesor marca en qué trimestres se habilita cada
 * lección; el sistema la habilita o deshabilita según la fecha. Si el profesor la cambia a mano
 * en el catálogo, el plan ya no la toca hasta que la devuelva al plan.
 */

import { useMemo, useState } from 'react';
import { Loader2, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { LeccionSalon, PlanTrimestres } from '@/types/nucleo';
import { nombreLeccion } from '@/lib/leccionesSalon';

interface Props {
  catalogo: LeccionSalon[];
  plan: PlanTrimestres;
  gradoSalon: number;
  soloLectura: boolean;
  onGuardar: (plan: Record<string, number[]>) => Promise<void>;
  onDevolver: (leccionId: string) => void;
}

const fecha = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('es-PA', { day: 'numeric', month: 'short' });

export function PlanTrimestre({ catalogo, plan, gradoSalon, soloLectura, onGuardar, onDevolver }: Props) {
  const [borrador, setBorrador] = useState<Record<string, number[]>>(plan.plan);
  const [verTodas, setVerTodas] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lecciones del grado del salón con ejercicios, más las que ya están en el plan
  const filas = useMemo(() => catalogo
    .filter((l) => l.incluida && (borrador[l.id] || plan.plan[l.id] || verTodas || (l.grado === gradoSalon && l.tiene_generador)))
    .sort((a, b) => a.orden_programa - b.orden_programa), [catalogo, borrador, plan.plan, verTodas, gradoSalon]);

  const cambio = JSON.stringify(normalizar(borrador)) !== JSON.stringify(normalizar(plan.plan));
  const alternar = (id: string, t: number) => {
    const actual = new Set(borrador[id] ?? []);
    if (actual.has(t)) actual.delete(t); else actual.add(t);
    setBorrador({ ...borrador, [id]: [...actual].sort() });
  };

  const guardar = async () => {
    setError(null);
    setGuardando(true);
    try {
      await onGuardar(normalizar(borrador));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo guardar el plan.');
    } finally {
      setGuardando(false);
    }
  };

  const vigente = plan.trimestres.find((t) => t.numero === plan.vigente);
  return (
    <div className="space-y-4">
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          <strong className="text-foreground">Opcional.</strong> Marca en qué trimestres se practica cada lección y el
          sistema la habilita o deshabilita sola cuando cambia el trimestre. No hay un plan por defecto.
        </p>
        <p>
          Si habilitas o deshabilitas una lección a mano en el catálogo, el plan deja de tocarla (verás «Ajuste manual»)
          hasta que la devuelvas al plan.
        </p>
        <p data-testid="trimestre-vigente">
          {vigente
            ? <>Trimestre vigente: <strong className="text-foreground">T{vigente.numero}</strong> ({fecha(vigente.inicio)} – {fecha(vigente.fin)}).</>
            : 'El año todavía no empezó: el plan se aplicará desde el primer trimestre.'}
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs">
            <tr>
              <th className="px-4 py-2">Lección</th>
              {plan.trimestres.map((t) => (
                <th key={t.numero} className="px-2 py-2 text-center" title={`${fecha(t.inicio)} – ${fecha(t.fin)}`}>
                  T{t.numero}{t.numero === plan.vigente && ' ●'}
                </th>
              ))}
              <th className="px-4 py-2">Hoy</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filas.map((l) => {
              const enPlan = (borrador[l.id] ?? []).length > 0;
              return (
                <tr key={l.id} data-testid={`plan-${l.id}`}>
                  <td className="px-4 py-2">{nombreLeccion(l)}</td>
                  {plan.trimestres.map((t) => (
                    <td key={t.numero} className="px-2 py-2 text-center">
                      <input type="checkbox" className="h-5 w-5 accent-primary" disabled={soloLectura}
                        aria-label={`${l.leccion_titulo} en el trimestre ${t.numero}`}
                        checked={(borrador[l.id] ?? []).includes(t.numero)} onChange={() => alternar(l.id, t.numero)} />
                    </td>
                  ))}
                  <td className="px-4 py-2 text-xs">
                    <span className={l.habilitada ? 'text-emerald-700' : 'text-muted-foreground'}>
                      {l.habilitada ? 'Habilitada' : 'Deshabilitada'}
                    </span>
                    {enPlan && (l.ajuste_manual ? (
                      <span className="ml-1">
                        · Ajuste manual
                        {!soloLectura && (
                          <Button size="sm" variant="ghost" className="ml-1 h-7 px-2" onClick={() => onDevolver(l.id)}>
                            <RotateCcw className="mr-1 h-3 w-3" /> Devolver al plan
                          </Button>
                        )}
                      </span>
                    ) : <span className="text-muted-foreground"> · según el plan</span>)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <label className="flex min-h-[40px] items-center gap-2 text-sm">
        <input type="checkbox" checked={verTodas} onChange={(e) => setVerTodas(e.target.checked)} />
        Ver también lecciones de otros grados y sin ejercicios
      </label>

      {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>}
      {!soloLectura && (
        <div className="flex justify-end gap-2">
          <Button variant="outline" disabled={!cambio || guardando} onClick={() => setBorrador(plan.plan)}>Descartar cambios</Button>
          <Button disabled={!cambio || guardando} onClick={guardar}>
            {guardando && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Guardar plan
          </Button>
        </div>
      )}
    </div>
  );
}

function normalizar(plan: Record<string, number[]>): Record<string, number[]> {
  return Object.fromEntries(
    Object.entries(plan).filter(([, ts]) => ts.length > 0).sort(([a], [b]) => a.localeCompare(b)).map(([k, ts]) => [k, [...ts].sort()]),
  );
}
