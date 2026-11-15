/**
 * Avance del salón (fase 6b). En vez de una hoja de cálculo de estudiantes × lecciones:
 * - "Por lección": una barra apilada por lección con sus conteos; al tocarla se ven los estudiantes
 *   agrupados por estado (cada nombre abre la ficha).
 * - "Por estudiante": una fila por estudiante, primero quien necesita atención.
 * Con un trimestre elegido muestra lo que pasó en ese periodo.
 * "Por confirmar" (fase 7a): lo que el diagnóstico inicial dio por sabido; no cuenta en "dominan".
 */

import { Fragment, useState } from 'react';
import { ChevronDown, ChevronRight, Sparkles, Star, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { EstadoVisible, FilaAvanceLeccion, Seguimiento } from '@/types/nucleo';
import { COLOR_ESTADO, ESTADOS, ETIQUETA_ESTADO, agruparAvance, porcentaje } from '@/lib/seguimiento';
import { formatearFecha } from '@/lib/fechas';

interface Props {
  datos: Seguimiento;
  onAbrirFicha: (estudianteId: number) => void;
}

export function BarraEstados({ conteos, total }: { conteos: Record<EstadoVisible, number>; total: number }) {
  return (
    <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100" role="img"
      aria-label={ESTADOS.map((e) => `${ETIQUETA_ESTADO[e]}: ${conteos[e]}`).join(', ')}>
      {total > 0 && ESTADOS.map((e) => conteos[e] > 0 && (
        <div key={e} className={COLOR_ESTADO[e].barra} style={{ width: `${(conteos[e] / total) * 100}%` }} />
      ))}
    </div>
  );
}

export function TablaAvance({ datos, onAbrirFicha }: Props) {
  const [vista, setVista] = useState<'leccion' | 'estudiante'>('leccion');
  const [menorDominio, setMenorDominio] = useState(false);
  const nombres = new Map(datos.estudiantes.map((e) => [e.id, e.nombre]));

  if (datos.por_leccion.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Todavía no hay lecciones habilitadas en el salón.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1" role="group" aria-label="Vista">
          <Button size="sm" variant={vista === 'leccion' ? 'default' : 'outline'} aria-pressed={vista === 'leccion'}
            className="min-h-[40px]" onClick={() => setVista('leccion')}>Por lección</Button>
          <Button size="sm" variant={vista === 'estudiante' ? 'default' : 'outline'} aria-pressed={vista === 'estudiante'}
            className="min-h-[40px]" onClick={() => setVista('estudiante')}>Por estudiante</Button>
        </div>
        {vista === 'leccion' && !datos.periodo && (
          <label className="flex min-h-[40px] items-center gap-2 text-sm">
            <input type="checkbox" checked={menorDominio} onChange={(e) => setMenorDominio(e.target.checked)} />
            Primero las menos dominadas
          </label>
        )}
      </div>

      {!datos.periodo && <Leyenda />}

      {vista === 'leccion' && datos.periodo && <TablaPeriodo datos={datos} nombres={nombres} onAbrirFicha={onAbrirFicha} />}
      {vista === 'leccion' && !datos.periodo && agruparAvance(datos.por_leccion, menorDominio).map((g) => (
        <section key={g.clave} className="rounded-lg border" aria-label={g.titulo}>
          <h3 className="border-b bg-muted/40 px-4 py-2 text-sm font-semibold">{g.titulo}</h3>
          <ul className="divide-y">
            {g.filas.map((f) => <FilaLeccion key={f.leccion_id} fila={f} nombres={nombres} onAbrirFicha={onAbrirFicha} />)}
          </ul>
        </section>
      ))}
      {vista === 'estudiante' && <PorEstudiante datos={datos} onAbrirFicha={onAbrirFicha} />}
    </div>
  );
}

function Leyenda() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
      {ESTADOS.map((e) => (
        <span key={e} className="inline-flex items-center gap-1">
          <span className={`h-2.5 w-2.5 rounded-full ${COLOR_ESTADO[e].barra}`} /> {ETIQUETA_ESTADO[e]}
        </span>
      ))}
    </div>
  );
}

function FilaLeccion({ fila: f, nombres, onAbrirFicha }: {
  fila: FilaAvanceLeccion; nombres: Map<number, string>; onAbrirFicha: Props['onAbrirFicha'];
}) {
  const [abierta, setAbierta] = useState(false);
  const Icono = abierta ? ChevronDown : ChevronRight;
  return (
    <li data-testid={`avance-${f.leccion_id}`}>
      <button type="button" className="grid w-full gap-2 px-4 py-3 text-left hover:bg-muted/30 md:grid-cols-[minmax(0,1fr)_16rem] md:items-center"
        aria-expanded={abierta} onClick={() => setAbierta(!abierta)}>
        <span className="flex min-w-0 items-start gap-2">
          <Icono className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <span className="min-w-0">
            <span className="font-medium">L{f.leccion_numero}. {f.titulo}</span>
            {f.prioritaria && <Star className="ml-1 inline h-3.5 w-3.5 fill-amber-400 align-[-2px] text-amber-500" aria-label="Prioritaria" />}
            <span className="block text-xs text-muted-foreground">
              {f.dominan} de {f.total} dominan
              {f.conteos.repaso > 0 && ` · ${f.conteos.repaso} en repaso`}
              {f.conteos.por_confirmar > 0 && ` · ${f.conteos.por_confirmar} por confirmar`}
              {f.conteos.en_progreso > 0 && ` · ${f.conteos.en_progreso} en progreso`}
            </span>
          </span>
        </span>
        <span className="flex items-center gap-2">
          <BarraEstados conteos={f.conteos} total={f.total} />
          <span className="w-12 text-right text-sm font-semibold tabular-nums">{porcentaje(f.porcentaje_dominan)}</span>
        </span>
      </button>
      {abierta && (
        <div className="grid gap-3 border-t bg-muted/10 px-4 py-3 sm:grid-cols-2 lg:grid-cols-5">
          {ESTADOS.map((e) => (
            <div key={e}>
              <p className="mb-1 text-xs font-semibold">{ETIQUETA_ESTADO[e]} ({f.estudiantes[e].length})</p>
              <div className="flex flex-wrap gap-1">
                {f.estudiantes[e].length === 0 && <span className="text-xs text-muted-foreground">—</span>}
                {f.estudiantes[e].map((id) => (
                  <button key={id} type="button" onClick={() => onAbrirFicha(id)}
                    className={`rounded-full border px-2 py-1 text-xs hover:underline ${COLOR_ESTADO[e].chip}`}>
                    {nombres.get(id) ?? id}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </li>
  );
}

function PorEstudiante({ datos, onAbrirFicha }: Props) {
  return (
    <ul className="divide-y rounded-lg border">
      {datos.por_estudiante.map((e) => {
        const dominan = e.conteos.dominado + e.conteos.repaso;
        return (
          <li key={e.estudiante_id} data-testid={`avance-est-${e.estudiante_id}`}
            className="grid gap-2 px-4 py-3 md:grid-cols-[14rem_minmax(0,1fr)_auto] md:items-center">
            <div>
              <p className="font-medium">{e.nombre}</p>
              <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {e.codigo}
                {datos.diagnosticos?.[String(e.estudiante_id)] && (
                  <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-sky-800"
                    data-testid={`diag-${e.estudiante_id}`}>
                    {datos.diagnosticos[String(e.estudiante_id)] === 'en_curso' ? 'Diagnóstico en curso' : 'Diagnóstico pendiente'}
                  </span>
                )}
              </p>
            </div>
            <div className="space-y-1">
              <BarraEstados conteos={e.conteos} total={e.total} />
              <p className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
                <span>Domina {dominan} de {e.total}</span>
                {e.conteos.repaso > 0 && <span>{e.conteos.repaso} en repaso</span>}
                {e.conteos.por_confirmar > 0 && <span>{e.conteos.por_confirmar} por confirmar</span>}
                {e.conteos.en_progreso > 0 && <span>{e.conteos.en_progreso} en progreso</span>}
                {e.alertas_dificultad > 0 && (
                  <span className="inline-flex items-center gap-1 font-medium text-red-700">
                    <TriangleAlert className="h-3 w-3" /> Dificultad en {e.alertas_dificultad}
                  </span>
                )}
                {e.alertas_excelencia > 0 && (
                  <span className="inline-flex items-center gap-1 font-medium text-violet-700">
                    <Sparkles className="h-3 w-3" /> Sobresale en {e.alertas_excelencia}
                  </span>
                )}
              </p>
            </div>
            <Button size="sm" variant="outline" className="min-h-[40px] justify-self-start md:justify-self-end"
              onClick={() => onAbrirFicha(e.estudiante_id)}>Ficha</Button>
          </li>
        );
      })}
    </ul>
  );
}

function TablaPeriodo({ datos, nombres, onAbrirFicha }: Props & { nombres: Map<number, string> }) {
  const periodo = datos.periodo!;
  const fecha = (iso: string) => formatearFecha(iso);
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground">
        Trimestre {periodo.numero} ({fecha(periodo.inicio)} – {fecha(periodo.fin)}): qué se practicó y quién dominó cada lección en ese periodo.
      </p>
      {periodo.por_leccion.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No hubo práctica en este trimestre.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs">
              <tr>
                <th className="px-4 py-2">Lección</th>
                <th className="px-2 py-2 text-right">Practicaron</th>
                <th className="px-2 py-2 text-right">Problemas</th>
                <th className="px-2 py-2 text-right">Acierto</th>
                <th className="px-4 py-2">La dominaron en el trimestre</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {periodo.por_leccion.map((f) => (
                <Fragment key={f.leccion_id}>
                  <tr data-testid={`periodo-${f.leccion_id}`}>
                    <td className="px-4 py-2">{f.grado}.º U{f.unidad_numero} L{f.leccion_numero} · {f.titulo}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{f.practicaron}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{f.problemas}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{porcentaje(f.precision)}</td>
                    <td className="px-4 py-2">
                      {f.dominaron.length === 0 ? '—' : f.dominaron.map((id, i) => (
                        <Fragment key={id}>
                          {i > 0 && ', '}
                          <button type="button" className="underline-offset-2 hover:underline" onClick={() => onAbrirFicha(id)}>
                            {nombres.get(id) ?? id}
                          </button>
                        </Fragment>
                      ))}
                    </td>
                  </tr>
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
