/**
 * Ajustes por estudiante: lecciones asignadas solo a él (se cierran solas al dominarlas o a mano)
 * y el banco de respuestas forzado como adaptación de accesibilidad.
 */

import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { AjusteEstudiante, AsignacionNucleo, LeccionSalon } from '@/types/nucleo';
import type { EstudianteDelSalon } from '@/types';
import { nombreLeccion } from '@/lib/leccionesSalon';

interface Props {
  estudiantes: EstudianteDelSalon[];
  catalogo: LeccionSalon[];
  asignaciones: AsignacionNucleo[];
  ajustes: AjusteEstudiante[];
  soloLectura: boolean;
  onAsignar: (estudianteId: number, leccionId: string) => void;
  onCerrar: (asignacionId: number) => void;
  onForzarBanco: (estudianteId: number, forzar: boolean) => void;
}

const ESTADO_CERRADA: Record<string, string> = {
  cerrada_por_dominio: 'la dominó',
  cancelada: 'cerrada a mano',
};

const fecha = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('es-PA', { day: 'numeric', month: 'short' }) : '';

export function PorEstudiante({ estudiantes, catalogo, asignaciones, ajustes, soloLectura, onAsignar, onCerrar, onForzarBanco }: Props) {
  const asignables = catalogo
    .filter((l) => l.incluida && l.tiene_generador)
    .sort((a, b) => a.orden_programa - b.orden_programa);
  const cerradas = asignaciones
    .filter((a) => a.estado !== 'activa')
    .sort((a, b) => (b.fecha_cierre ?? '').localeCompare(a.fecha_cierre ?? ''))
    .slice(0, 8);

  if (estudiantes.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">El salón todavía no tiene estudiantes.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1 text-sm text-muted-foreground">
        <p>
          <strong className="text-foreground">Asignar una lección</strong> la agrega a la práctica de ese estudiante
          aunque no esté habilitada para el salón. Se cierra sola cuando la domina; también puedes cerrarla tú.
        </p>
        <p>
          <strong className="text-foreground">Siempre con opciones</strong> muestra opciones para elegir en lugar del
          teclado. Úsalo como adaptación para quien escribir números le cuesta.
        </p>
      </div>

      <ul className="divide-y rounded-lg border">
        {estudiantes.map((e) => {
          const activas = asignaciones.filter((a) => a.estudiante_id === e.estudiante_id && a.estado === 'activa');
          const banco = ajustes.find((a) => a.estudiante_id === e.estudiante_id)?.banco_forzado ?? false;
          return (
            <FilaEstudiante key={e.estudiante_id} estudiante={e} activas={activas} banco={banco}
              asignables={asignables.filter((l) => !activas.some((a) => a.leccion_id === l.id))}
              soloLectura={soloLectura} onAsignar={onAsignar} onCerrar={onCerrar} onForzarBanco={onForzarBanco} />
          );
        })}
      </ul>

      {cerradas.length > 0 && (
        <div className="text-sm">
          <h3 className="mb-1 font-semibold">Asignaciones cerradas recientemente</h3>
          <ul className="space-y-1 text-muted-foreground">
            {cerradas.map((a) => (
              <li key={a.id}>
                {a.estudiante_nombre} · {a.leccion_titulo} · {ESTADO_CERRADA[a.estado]} el {fecha(a.fecha_cierre)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function FilaEstudiante({ estudiante: e, activas, banco, asignables, soloLectura, onAsignar, onCerrar, onForzarBanco }: {
  estudiante: EstudianteDelSalon; activas: AsignacionNucleo[]; banco: boolean; asignables: LeccionSalon[];
  soloLectura: boolean; onAsignar: Props['onAsignar']; onCerrar: Props['onCerrar']; onForzarBanco: Props['onForzarBanco'];
}) {
  const [eleccion, setEleccion] = useState('');
  return (
    <li className="grid gap-3 px-4 py-3 md:grid-cols-[12rem_1fr_auto] md:items-start" data-testid={`estudiante-${e.estudiante_id}`}>
      <div>
        <p className="font-medium">{e.nombre_completo}</p>
        <p className="text-xs text-muted-foreground">{e.codigo_estudiante}</p>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {activas.length === 0 && <span className="text-sm text-muted-foreground">Sin lecciones asignadas.</span>}
          {activas.map((a) => (
            <span key={a.id} className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-3 py-1 text-sm">
              {a.leccion_titulo}
              {!soloLectura && (
                <button type="button" aria-label={`Cerrar ${a.leccion_titulo} de ${e.nombre_completo}`}
                  className="ml-1 rounded-full p-1 hover:bg-muted" onClick={() => onCerrar(a.id)}>
                  <X className="h-3 w-3" />
                </button>
              )}
            </span>
          ))}
        </div>
        {!soloLectura && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <select aria-label={`Lección para ${e.nombre_completo}`} value={eleccion}
              onChange={(ev) => setEleccion(ev.target.value)}
              className="min-h-[40px] w-full min-w-0 flex-1 rounded-md border bg-background px-2 text-sm">
              <option value="">Asignar una lección…</option>
              {asignables.map((l) => <option key={l.id} value={l.id}>{nombreLeccion(l)}</option>)}
            </select>
            <Button size="sm" variant="outline" className="min-h-[40px]" disabled={!eleccion}
              onClick={() => { onAsignar(e.estudiante_id, eleccion); setEleccion(''); }}>
              Asignar
            </Button>
          </div>
        )}
      </div>

      <label className="flex min-h-[40px] items-center gap-2 text-sm md:justify-end">
        <input type="checkbox" role="switch" className="h-5 w-5 accent-primary" checked={banco} disabled={soloLectura}
          aria-label={`Siempre con opciones para ${e.nombre_completo}`}
          onChange={(ev) => onForzarBanco(e.estudiante_id, ev.target.checked)} />
        Siempre con opciones
      </label>
    </li>
  );
}
