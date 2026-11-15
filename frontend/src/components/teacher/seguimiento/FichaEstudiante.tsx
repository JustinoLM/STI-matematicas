/**
 * Ficha del estudiante en el núcleo (fase 6b): dominio por camino y por lección, errores más
 * frecuentes con nombres para docentes, asignaciones, ajustes, sesiones recientes y un resumen de
 * sus años lectivos anteriores (solo lectura).
 */

import { History, ListChecks, TriangleAlert } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { FichaEstudiante as Ficha } from '@/types/nucleo';
import { COLOR_ESTADO, ESTADO_UNO, fechaDelServidor, porcentaje } from '@/lib/seguimiento';

const fechaCorta = (iso: string | null) =>
  iso ? fechaDelServidor(iso).toLocaleDateString('es-PA', { day: 'numeric', month: 'short' }) : '—';

const minutos = (inicio: string, fin: string | null) =>
  fin ? Math.max(1, Math.round((fechaDelServidor(fin).getTime() - fechaDelServidor(inicio).getTime()) / 60000)) : null;

const ESTADO_SESION: Record<string, string> = { completada: 'Completada', abandonada: 'Descartada', activa: 'A medias' };
const ESTADO_ASIGNACION: Record<string, string> = { activa: 'Abierta', cerrada_por_dominio: 'La dominó', cancelada: 'Cerrada a mano' };

export function FichaEstudiante({ ficha }: { ficha: Ficha }) {
  const conPeriodo = ficha.periodo !== null;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2 text-sm">
        <span className="rounded-full border px-3 py-1">
          {ficha.banco_forzado ? 'Siempre con opciones para elegir (adaptación)' : 'Sin adaptaciones'}
        </span>
        {ficha.asignaciones.filter((a) => a.estado === 'activa').map((a) => (
          <span key={a.id} className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-sky-800">
            Asignada: {a.leccion_titulo}
          </span>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">Por camino</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {ficha.por_camino.length === 0 && <p className="text-sm text-muted-foreground">Sin lecciones en práctica.</p>}
          {ficha.por_camino.map((c) => (
            <div key={c.camino} data-testid={`camino-${c.camino}`} className="grid items-center gap-2 sm:grid-cols-[12rem_minmax(0,1fr)_7rem]">
              <span className="text-sm font-medium">{c.nombre}</span>
              <div className="flex h-3 overflow-hidden rounded-full bg-slate-100">
                <div className="bg-emerald-500" style={{ width: `${c.total ? (c.dominadas / c.total) * 100 : 0}%` }} />
                <div className="bg-amber-400" style={{ width: `${c.total ? (c.en_progreso / c.total) * 100 : 0}%` }} />
              </div>
              <span className="text-xs text-muted-foreground sm:text-right">domina {c.dominadas} de {c.total}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">Por lección</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs">
              <tr>
                <th className="px-4 py-2">Lección</th>
                <th className="px-2 py-2">Estado</th>
                <th className="px-2 py-2 text-right">{conPeriodo ? 'En el trimestre' : 'Últimos problemas'}</th>
                <th className="px-2 py-2 text-right">Extensión</th>
                <th className="px-4 py-2 text-right">Última práctica</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {ficha.lecciones.map((l) => {
                const [aciertos, problemas] = conPeriodo
                  ? [l.aciertos_periodo, l.problemas_periodo] : [l.aciertos_recientes, l.problemas_recientes];
                return (
                  <tr key={l.leccion_id} data-testid={`ficha-leccion-${l.leccion_id}`}>
                    <td className="px-4 py-2">
                      {l.grado}.º U{l.unidad_numero} L{l.leccion_numero} · {l.titulo}
                      {l.asignada && <span className="ml-1 text-xs text-sky-700">(asignada)</span>}
                      {!l.habilitada && !l.asignada && <span className="ml-1 text-xs text-muted-foreground">(no habilitada)</span>}
                    </td>
                    <td className="px-2 py-2">
                      <span className={`whitespace-nowrap rounded-full border px-2 py-0.5 text-xs ${COLOR_ESTADO[l.estado].chip}`}>{ESTADO_UNO[l.estado]}</span>
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums">{problemas ? `${aciertos} de ${problemas}` : '—'}</td>
                    <td className="px-2 py-2 text-right tabular-nums">
                      {l.extension_problemas ? `${l.extension_aciertos} de ${l.extension_problemas}` : '—'}
                    </td>
                    <td className="px-4 py-2 text-right">{fechaCorta(l.ultima_practica)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><TriangleAlert className="h-5 w-5" /> Errores más frecuentes</CardTitle></CardHeader>
          <CardContent>
            {ficha.errores.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin errores registrados {conPeriodo ? 'en este trimestre' : 'este año'}.</p>
            ) : (
              <ol className="space-y-2">
                {ficha.errores.map((e) => (
                  <li key={e.codigo} className="flex items-start justify-between gap-3 text-sm" data-testid="error-frecuente">
                    <span>
                      {e.descripcion}
                      {e.camino_nombre && <span className="block text-xs text-muted-foreground">{e.camino_nombre}</span>}
                    </span>
                    <span className="whitespace-nowrap font-semibold tabular-nums">{e.veces} {e.veces === 1 ? 'vez' : 'veces'}</span>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><ListChecks className="h-5 w-5" /> Sesiones recientes</CardTitle></CardHeader>
          <CardContent>
            {ficha.sesiones.length === 0 ? <p className="text-sm text-muted-foreground">Todavía no practicó este año.</p> : (
              <ul className="space-y-1 text-sm">
                {ficha.sesiones.map((s) => {
                  const m = minutos(s.fecha_inicio, s.fecha_fin);
                  return (
                    <li key={s.id} className="flex justify-between gap-2">
                      <span>{fechaCorta(s.fecha_inicio)} · {s.problemas} de {s.cantidad_problemas} {s.cantidad_problemas === 1 ? 'problema' : 'problemas'} · {s.aciertos} {s.aciertos === 1 ? 'acierto' : 'aciertos'}{m ? ` · ${m} min` : ''}</span>
                      <span className="text-muted-foreground">{ESTADO_SESION[s.estado] ?? s.estado}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {ficha.asignaciones.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Asignaciones</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {ficha.asignaciones.map((a) => (
                <li key={a.id}>
                  {a.leccion_titulo} · desde el {fechaCorta(a.fecha_asignacion)} · {ESTADO_ASIGNACION[a.estado]}
                  {a.fecha_cierre && ` el ${fechaCorta(a.fecha_cierre)}`}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><History className="h-5 w-5" /> Años anteriores</CardTitle></CardHeader>
        <CardContent>
          {ficha.anios_anteriores.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tiene años anteriores en el STI.</p>
          ) : (
            <ul className="space-y-1 text-sm" data-testid="anios-anteriores">
              {ficha.anios_anteriores.map((a) => (
                <li key={a.anio_lectivo_id}>
                  {a.anio} · Salón {a.salon} ({a.grado}.º) · {a.lecciones_dominadas} lecciones dominadas ·{' '}
                  {a.problemas} problemas ({porcentaje(a.problemas ? a.aciertos / a.problemas : null)} de acierto)
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
