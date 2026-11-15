/**
 * Diagnóstico inicial en la ficha del estudiante (fase 7a).
 *
 * - Qué se tomó por sabido y qué no: las lecciones probadas (✓ / ✗), las inferidas por el grafo de
 *   prerrequisitos y las que quedaron sin decidir.
 * - Qué pasó después con cada provisional: por confirmar, confirmado o retirado. Retirado se
 *   muestra como información neutra, no como alerta.
 * - Acciones: repetir el diagnóstico (se hace la próxima vez que el estudiante entre), cerrarlo con
 *   lo obtenido si quedó a medias, o cancelarlo.
 */

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, ClipboardCheck, Loader2, Minus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatearFecha } from '@/lib/fechas';
import { clavesProfesor, nucleoProfesorService } from '@/services/nucleoService';
import type { DiagnosticoFicha as Diagnostico, DiagnosticoLeccion } from '@/types/nucleo';

const ESTADO: Record<Diagnostico['estado'], string> = {
  pendiente: 'Pendiente: lo hará la próxima vez que entre a practicar',
  en_curso: 'A medias: lo retomará la próxima vez que entre',
  terminado: 'Terminado',
  cerrado: 'Cerrado por el profesor con lo obtenido',
  cancelado: 'Cancelado (no se aplicó nada)',
};

const MOTIVO: Record<string, string> = {
  tope_problemas: 'llegó al máximo de problemas',
  tope_tiempo: 'llegó al máximo de tiempo',
};

const SEGUIMIENTO: Record<string, { texto: string; clase: string }> = {
  por_confirmar: { texto: 'Por confirmar', clase: 'border-sky-200 bg-sky-50 text-sky-800' },
  confirmado: { texto: 'Confirmada con la práctica', clase: 'border-emerald-200 bg-emerald-50 text-emerald-800' },
  retirado: { texto: 'La práctica mostró que aún no la domina', clase: 'border-slate-200 bg-slate-50 text-slate-700' },
};

function nombre(l: DiagnosticoLeccion) {
  return l.grado ? `${l.grado}.º U${l.unidad_numero} L${l.leccion_numero} · ${l.titulo}` : l.titulo;
}

function Grupo({ titulo, lecciones, testid, icono }: {
  titulo: string; lecciones: DiagnosticoLeccion[]; testid: string; icono: (l: DiagnosticoLeccion) => React.ReactNode;
}) {
  if (lecciones.length === 0) return null;
  return (
    <div data-testid={testid}>
      <p className="mb-1 text-sm font-semibold">{titulo} ({lecciones.length})</p>
      <ul className="space-y-1 text-sm">
        {lecciones.map((l) => (
          <li key={l.leccion_id} className="flex items-start gap-2" data-testid={`diag-${l.leccion_id}`}>
            <span className="mt-0.5 w-4 shrink-0">{icono(l)}</span>
            <span className="min-w-0">
              {nombre(l)}
              {l.origen === 'probada' && l.problemas > 0 && (
                <span className="ml-1 text-xs text-muted-foreground">({l.aciertos} de {l.problemas})</span>
              )}
              {l.seguimiento && (
                <span className={`ml-2 inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-xs ${SEGUIMIENTO[l.seguimiento].clase}`}>
                  {SEGUIMIENTO[l.seguimiento].texto}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface Props {
  diagnostico: Diagnostico | null | undefined;
  anioId: number;
  estudianteId: number;
  soloLectura: boolean;
}

export function DiagnosticoFicha({ diagnostico: d, anioId, estudianteId, soloLectura }: Props) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const accion = useMutation({
    mutationFn: (a: 'pedir' | 'cerrar' | 'cancelar') => nucleoProfesorService.diagnostico(anioId, estudianteId, a),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: clavesProfesor.salon(anioId) });
    },
    onError: (e: Error) => setError(e.message),
  });

  const abierto = d && (d.estado === 'pendiente' || d.estado === 'en_curso');
  const probadas = d?.lecciones.filter((l) => l.origen === 'probada') ?? [];
  const inferidas = d?.lecciones.filter((l) => l.origen === 'inferida' && l.decision === 'sabida') ?? [];
  const inferidasNo = d?.lecciones.filter((l) => l.origen === 'inferida' && l.decision === 'no_sabida') ?? [];
  const sinDecidir = d?.lecciones.filter((l) => l.decision === 'sin_decidir') ?? [];
  const previas = d?.lecciones.filter((l) => l.origen === 'previa') ?? [];

  return (
    <Card data-testid="diagnostico-ficha">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg"><ClipboardCheck className="h-5 w-5" /> Diagnóstico inicial</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!d ? (
          <p className="text-sm text-muted-foreground">
            No hizo diagnóstico en este salón. Lo hace solo la primera vez que entra a practicar; puedes pedir uno.
          </p>
        ) : (
          <>
            <p className="text-sm">
              <span className="font-medium">{ESTADO[d.estado]}</span>
              {d.motivo_fin && MOTIVO[d.motivo_fin] && <span className="text-muted-foreground"> ({MOTIVO[d.motivo_fin]})</span>}
              {d.origen === 'profesor' && <span className="text-muted-foreground"> · lo pediste tú</span>}
            </p>
            {(d.problemas > 0 || d.fecha_fin) && (
              <p className="text-sm text-muted-foreground">
                {formatearFecha(d.fecha_fin ?? d.fecha_inicio ?? d.fecha_creacion)} · {d.problemas}{' '}
                {d.problemas === 1 ? 'problema' : 'problemas'} · {Math.max(1, Math.round(d.minutos))} min de trabajo
              </p>
            )}
            {d.lecciones.length > 0 && (
              <div className="grid gap-4 md:grid-cols-2">
                <Grupo titulo="Probadas" lecciones={probadas} testid="diag-probadas"
                  icono={(l) => <IconoProbada sabida={l.decision === 'sabida'} />} />
                <Grupo titulo="Se dan por sabidas (prerrequisitos de una que resolvió bien)" lecciones={inferidas}
                  testid="diag-inferidas" icono={() => <Check className="h-4 w-4 text-emerald-600" />} />
                <Grupo titulo="Todavía no (dependen de una que no resolvió)" lecciones={inferidasNo}
                  testid="diag-inferidas-no" icono={() => <Minus className="h-4 w-4 text-slate-400" />} />
                <Grupo titulo={abierto ? 'Por decidir' : 'Sin decidir: las descubrirá la práctica'} lecciones={sinDecidir}
                  testid="diag-sin-decidir" icono={() => <Minus className="h-4 w-4 text-slate-400" />} />
                <Grupo titulo="Ya las dominaba" lecciones={previas} testid="diag-previas"
                  icono={() => <Check className="h-4 w-4 text-emerald-600" />} />
              </div>
            )}
            {probadas.length > 0 && (
              <p className="text-xs text-muted-foreground">
                En las probadas, ✓ la resolvió bien y ✗ todavía no. Lo que el diagnóstico da por sabido queda
                «Por confirmar»: la práctica lo confirma o lo retira sola.
              </p>
            )}
          </>
        )}
        {!soloLectura && (
          <div className="flex flex-wrap items-center gap-2">
            {!abierto && (
              <Button size="sm" variant="outline" className="min-h-[40px]" disabled={accion.isPending}
                onClick={() => accion.mutate('pedir')}>
                {d ? 'Repetir diagnóstico' : 'Pedir diagnóstico'}
              </Button>
            )}
            {d?.estado === 'en_curso' && (
              <Button size="sm" variant="outline" className="min-h-[40px]" disabled={accion.isPending}
                onClick={() => accion.mutate('cerrar')}>
                Cerrar con lo obtenido
              </Button>
            )}
            {abierto && (
              <Button size="sm" variant="ghost" className="min-h-[40px]" disabled={accion.isPending}
                onClick={() => accion.mutate('cancelar')}>
                Cancelar diagnóstico
              </Button>
            )}
            {accion.isPending && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            {error && <p className="text-sm text-red-700">{error}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** Ícono de una lección probada (✓ sabida, ✗ no sabida) */
export function IconoProbada({ sabida }: { sabida: boolean }) {
  return sabida ? <Check className="h-4 w-4 text-emerald-600" aria-label="Bien" />
    : <X className="h-4 w-4 text-slate-500" aria-label="Todavía no" />;
}
