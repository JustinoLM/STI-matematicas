/**
 * Catálogo de lecciones del salón: por defecto las del grado del salón, agrupadas por unidad.
 * Se pueden ver otros grados o solo las habilitadas. Cada fila se habilita con un interruptor y
 * abre el panel de configuración.
 */

import { useState } from 'react';
import { Info, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { LeccionSalon } from '@/types/nucleo';
import { agruparPorUnidad, habilidad, habilitadasPorGrado, insignias, resumenConfig } from '@/lib/leccionesSalon';

interface Props {
  catalogo: LeccionSalon[];
  gradoSalon: number;
  soloLectura: boolean;
  /** id de la lección cuyo interruptor está guardando */
  ocupada?: string | null;
  onCambiarHabilitada: (leccion: LeccionSalon, habilitar: boolean) => void;
  onAbrir: (leccion: LeccionSalon) => void;
}

const TONOS = {
  gris: 'border-slate-200 bg-slate-50 text-slate-700',
  ambar: 'border-amber-200 bg-amber-50 text-amber-800',
  azul: 'border-sky-200 bg-sky-50 text-sky-800',
};

export function CatalogoLecciones({ catalogo, gradoSalon, soloLectura, ocupada, onCambiarHabilitada, onAbrir }: Props) {
  const [grado, setGrado] = useState(gradoSalon);
  const [soloHabilitadas, setSoloHabilitadas] = useState(false);
  const unidades = agruparPorUnidad(catalogo, { grado, soloHabilitadas });
  const porGrado = habilitadasPorGrado(catalogo);
  const otrosGrados = Object.entries(porGrado).filter(([g]) => Number(g) !== grado);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Grado">
          <span className="mr-1 text-sm text-muted-foreground">Grado:</span>
          {[1, 2, 3, 4, 5, 6].map((g) => (
            <Button key={g} size="sm" variant={!soloHabilitadas && g === grado ? 'default' : 'outline'}
              className="min-h-[40px] min-w-[44px]" aria-pressed={!soloHabilitadas && g === grado}
              onClick={() => { setGrado(g); setSoloHabilitadas(false); }}>
              {g}.º{porGrado[g] ? <span className="ml-1 text-xs opacity-80">({porGrado[g]})</span> : null}
            </Button>
          ))}
        </div>
        <label className="flex min-h-[40px] items-center gap-2 text-sm">
          <input type="checkbox" checked={soloHabilitadas} onChange={(e) => setSoloHabilitadas(e.target.checked)} />
          Ver solo las habilitadas (todos los grados)
        </label>
      </div>

      {!soloHabilitadas && grado === gradoSalon && otrosGrados.length > 0 && (
        <p className="text-xs text-muted-foreground">
          También tienes habilitadas lecciones de otros grados:{' '}
          {otrosGrados.map(([g, n]) => `${n} de ${g}.º`).join(', ')}.
        </p>
      )}
      {!soloHabilitadas && grado !== gradoSalon && (
        <p className="flex items-center gap-2 rounded-md bg-sky-50 px-3 py-2 text-sm text-sky-800">
          <Info className="h-4 w-4 flex-shrink-0" />
          Estás viendo lecciones de {grado}.º. Puedes habilitarlas si parte del salón las necesita.
        </p>
      )}

      {unidades.length === 0 && (
        <p className="py-8 text-center text-sm text-muted-foreground">
          {soloHabilitadas ? 'Todavía no hay lecciones habilitadas.' : 'No hay lecciones en este grado.'}
        </p>
      )}

      {unidades.map((u) => (
        <section key={u.clave} className="rounded-lg border" aria-label={`Unidad ${u.numero}`}>
          <h3 className="border-b bg-muted/40 px-4 py-2 text-sm font-semibold">
            {soloHabilitadas && `${u.grado}.º · `}Unidad {u.numero} · {u.titulo}
          </h3>
          <ul className="divide-y">
            {u.lecciones.map((l) => (
              <FilaLeccion key={l.id} leccion={l} soloLectura={soloLectura} ocupada={ocupada === l.id}
                onCambiarHabilitada={onCambiarHabilitada} onAbrir={onAbrir} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function FilaLeccion({ leccion: l, soloLectura, ocupada, onCambiarHabilitada, onAbrir }: {
  leccion: LeccionSalon; soloLectura: boolean; ocupada: boolean;
  onCambiarHabilitada: Props['onCambiarHabilitada']; onAbrir: Props['onAbrir'];
}) {
  const resumen = l.habilitada ? resumenConfig(l) : '';
  return (
    <li className={`flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center ${l.incluida ? '' : 'opacity-60'}`}
      data-testid={`leccion-${l.id}`}>
      <div className="flex flex-1 items-start gap-3">
        {l.incluida ? (
          <input type="checkbox" role="switch" aria-label={`Habilitar ${l.leccion_titulo}`}
            className="mt-1 h-5 w-5 flex-shrink-0 accent-primary" checked={ocupada ? !l.habilitada : l.habilitada}
            disabled={soloLectura || ocupada} onChange={(e) => onCambiarHabilitada(l, e.target.checked)} />
        ) : (
          <span className="mt-1 h-5 w-5 flex-shrink-0" />
        )}
        <div className="min-w-0">
          <p className="font-medium">
            <span className="text-muted-foreground">L{l.leccion_numero}.</span> {l.leccion_titulo}
            {l.prioritaria && (
              <span className="ml-2 inline-flex items-center gap-1 text-xs font-semibold text-amber-600">
                <Star className="h-3 w-3 fill-amber-400" /> Prioritaria
              </span>
            )}
          </p>
          {l.incluida ? (
            <div className="mt-1 flex flex-wrap gap-1 text-xs">
              {l.caminos.map((c) => (
                <span key={c} className="rounded bg-muted px-2 py-0.5 text-muted-foreground">{habilidad(c)}</span>
              ))}
              {insignias(l).map((i) => (
                <span key={i.texto} title={i.detalle} className={`rounded border px-2 py-0.5 ${TONOS[i.tono]}`}>{i.texto}</span>
              ))}
              {l.prerrequisitos_editados && (
                <span className="rounded border border-violet-200 bg-violet-50 px-2 py-0.5 text-violet-800">
                  Prerrequisitos cambiados
                </span>
              )}
            </div>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">No se practica en el STI: {l.motivo_exclusion}</p>
          )}
          {resumen && <p className="mt-1 text-xs text-muted-foreground">{resumen}</p>}
        </div>
      </div>
      {l.incluida && (
        <Button size="sm" variant={l.habilitada ? 'outline' : 'ghost'} className="min-h-[40px] self-end sm:self-auto"
          onClick={() => onAbrir(l)}>
          {l.habilitada && !soloLectura ? 'Configurar' : 'Ver detalles'}
        </Button>
      )}
    </li>
  );
}
