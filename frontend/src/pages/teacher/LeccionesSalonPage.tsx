/**
 * Lecciones del salón (núcleo). De lo general a lo particular:
 * - Avance (fase 6b): tabla de dominio por lección o por estudiante, hoy o por trimestre.
 * - Alertas (fase 6b): dificultad y excelencia, con la acción que corresponde.
 * - Catálogo y Asignaciones (fase 6a): habilitar, configurar, prerrequisitos, asignaciones y banco.
 * - Plan por trimestre (fase 6b, opcional).
 * La pestaña va en la URL (?pestana=alertas) para poder enlazarla. Un año cerrado es de solo lectura.
 */

import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Lock, Star } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { clavesProfesor, nucleoProfesorService as api } from '@/services/nucleoService';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CatalogoLecciones } from '@/components/teacher/lecciones/CatalogoLecciones';
import { PanelLeccion } from '@/components/teacher/lecciones/PanelLeccion';
import { PorEstudiante } from '@/components/teacher/lecciones/PorEstudiante';
import { TablaAvance } from '@/components/teacher/seguimiento/TablaAvance';
import { ListaAlertas } from '@/components/teacher/seguimiento/ListaAlertas';
import { claveAlerta } from '@/lib/seguimiento';
import { PlanTrimestre } from '@/components/teacher/seguimiento/PlanTrimestre';
import { MAX_PRIORITARIAS, configDe, prioritarias } from '@/lib/leccionesSalon';
import type { AlertaNucleo, ConfigLeccion, LeccionSalon } from '@/types/nucleo';

const PESTANAS = ['avance', 'alertas', 'catalogo', 'estudiantes', 'plan'] as const;
type Pestana = (typeof PESTANAS)[number];

export default function LeccionesSalonPage() {
  const { id } = useParams<{ id: string }>();
  const anioId = parseInt(id || '0');
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [abierta, setAbierta] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trimestre, setTrimestre] = useState<number | null>(null);

  const { data: salon } = useQuery({
    queryKey: ['teacher', 'salon', anioId],
    queryFn: () => teacherService.getSalonDetalle(anioId),
    enabled: !!anioId,
  });
  const { data: catalogo, isLoading } = useQuery({
    queryKey: clavesProfesor.catalogo(anioId),
    queryFn: () => api.catalogo(anioId),
    enabled: !!anioId,
  });
  const { data: asignaciones = [] } = useQuery({
    queryKey: clavesProfesor.asignaciones(anioId),
    queryFn: () => api.asignaciones(anioId),
    enabled: !!anioId,
  });
  const { data: ajustes = [] } = useQuery({
    queryKey: clavesProfesor.ajustes(anioId),
    queryFn: () => api.ajustes(anioId),
    enabled: !!anioId,
  });
  const { data: seguimiento, isFetching: cargandoAvance } = useQuery({
    queryKey: clavesProfesor.seguimiento(anioId, trimestre),
    queryFn: () => api.seguimiento(anioId, trimestre),
    enabled: !!anioId,
    placeholderData: (previo) => previo,
  });
  const { data: alertas = [] } = useQuery({
    queryKey: clavesProfesor.alertas(anioId),
    queryFn: () => api.alertas(anioId),
    enabled: !!anioId,
  });
  const { data: plan } = useQuery({
    queryKey: clavesProfesor.plan(anioId),
    queryFn: () => api.plan(anioId),
    enabled: !!anioId,
  });

  /** Cualquier cambio puede mover la tabla, las alertas y el plan: se recarga todo lo del salón */
  const refrescarTodo = () => Promise.all([
    qc.invalidateQueries({ queryKey: clavesProfesor.salon(anioId) }),
    qc.invalidateQueries({ queryKey: clavesProfesor.alertasProfesor }),
  ]);
  const alFallar = (e: Error) => setError(e.message);
  const exito = () => { setError(null); return refrescarTodo(); };

  const habilitacion = useMutation({
    mutationFn: ({ leccion, habilitar }: { leccion: LeccionSalon; habilitar: boolean }) =>
      habilitar
        ? api.configurar(anioId, leccion.id, { ...configDe(leccion), prioritaria: false })
        : api.deshabilitar(anioId, leccion.id),
    // Se espera la recarga para que el interruptor no vuelva atrás un instante
    onSuccess: exito,
    onError: alFallar,
  });
  const asignar = useMutation({
    mutationFn: ({ estudianteId, leccionId }: { estudianteId: number; leccionId: string; clave?: string }) =>
      api.asignar(anioId, estudianteId, leccionId),
    onSuccess: exito,
    onError: alFallar,
  });
  const cerrar = useMutation({
    mutationFn: (asignacionId: number) => api.cerrarAsignacion(asignacionId),
    onSuccess: exito,
    onError: alFallar,
  });
  const banco = useMutation({
    mutationFn: ({ estudianteId, forzar }: { estudianteId: number; forzar: boolean }) =>
      api.forzarBanco(anioId, estudianteId, forzar),
    onSuccess: exito,
    onError: alFallar,
  });
  const habilitarDesdeAlerta = useMutation({
    mutationFn: ({ alerta }: { alerta: AlertaNucleo; clave: string }) => {
      const l = catalogo?.find((x) => x.id === alerta.leccion_id);
      const config = l ? configDe(l) : { signo: 'siempre' as const, iconos: 'siempre' as const, pistas: { 1: true, 2: true, 3: true }, prioritaria: false };
      return api.configurar(anioId, alerta.leccion_id, { ...config, prioritaria: false });
    },
    onSuccess: exito,
    onError: alFallar,
  });
  const ocultar = useMutation({
    mutationFn: ({ alerta }: { alerta: AlertaNucleo; clave: string }) =>
      api.ocultarAlerta(anioId, alerta.estudiante_id, alerta.leccion_id, alerta.tipo),
    onSuccess: exito,
    onError: alFallar,
  });

  const guardarPanel = async (leccion: LeccionSalon, cambios: { config: ConfigLeccion | null; prerrequisitos: string[] | null }) => {
    try {
      if (cambios.config) await api.configurar(anioId, leccion.id, cambios.config);
      if (cambios.prerrequisitos) await api.editarPrerrequisitos(anioId, leccion.id, cambios.prerrequisitos);
    } finally {
      refrescarTodo();
    }
  };
  const restaurar = async (leccion: LeccionSalon) => {
    await api.restaurarPrerrequisitos(anioId, leccion.id);
    refrescarTodo();
  };
  const guardarPlan = async (nuevo: Record<string, number[]>) => {
    await api.guardarPlan(anioId, nuevo);
    await refrescarTodo();
  };
  const devolver = useMutation({
    mutationFn: (leccionId: string) => api.devolverAlPlan(anioId, leccionId),
    onSuccess: exito,
    onError: alFallar,
  });

  if (isLoading || !catalogo || !salon) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const soloLectura = salon.cerrado;
  const leccionAbierta = catalogo.find((l) => l.id === abierta) ?? null;
  const nPrioritarias = prioritarias(catalogo).length;
  const nHabilitadas = catalogo.filter((l) => l.habilitada).length;
  const pedida = params.get('pestana') as Pestana | null;
  const pestana: Pestana = pedida && PESTANAS.includes(pedida) ? pedida : nHabilitadas > 0 ? 'avance' : 'catalogo';
  const abrirFicha = (estudianteId: number) => navigate(`/teacher/salones/${anioId}/estudiantes/${estudianteId}`);
  const ocupadaAlerta = asignar.isPending ? asignar.variables?.clave
    : habilitarDesdeAlerta.isPending ? habilitarDesdeAlerta.variables?.clave
    : ocultar.isPending ? ocultar.variables?.clave : null;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link to={`/teacher/salones/${anioId}`} className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="mr-1 h-4 w-4" /> Salón {salon.nombre}
        </Link>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Lecciones del salón {salon.nombre}</h1>
            <p className="text-sm text-muted-foreground">
              Cómo va el salón y qué practica. Una lección queda habilitada hasta que la desactives.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{nHabilitadas} habilitadas</Badge>
            <Badge variant="outline" className="gap-1" data-testid="contador-prioritarias">
              <Star className="h-3 w-3 fill-amber-400 text-amber-500" /> {nPrioritarias} de {MAX_PRIORITARIAS} prioritarias
            </Badge>
          </div>
        </div>
      </div>

      {soloLectura && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <Lock className="h-4 w-4 flex-shrink-0" />
          Este año lectivo está cerrado. Puedes consultarlo, pero no hacer cambios.
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</div>
      )}

      <Tabs value={pestana} onValueChange={(v) => setParams({ pestana: v }, { replace: true })}>
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 sm:w-auto">
          <TabsTrigger value="avance">Avance</TabsTrigger>
          <TabsTrigger value="alertas">
            Alertas{alertas.length > 0 && <span className="ml-1 rounded-full bg-red-100 px-1.5 text-xs text-red-700">{alertas.length}</span>}
          </TabsTrigger>
          <TabsTrigger value="catalogo">Catálogo</TabsTrigger>
          <TabsTrigger value="estudiantes">Asignaciones</TabsTrigger>
          <TabsTrigger value="plan">Plan por trimestre</TabsTrigger>
        </TabsList>

        <TabsContent value="avance" className="space-y-4 pt-4">
          <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Periodo">
            <span className="mr-1 text-sm text-muted-foreground">Periodo:</span>
            {[null, 1, 2, 3].map((t) => (
              <Button key={t ?? 'hoy'} size="sm" variant={trimestre === t ? 'default' : 'outline'} aria-pressed={trimestre === t}
                className="min-h-[40px] min-w-[52px]" onClick={() => setTrimestre(t)}>
                {t === null ? 'Hoy' : `T${t}`}
              </Button>
            ))}
            {cargandoAvance && <Loader2 className="ml-2 h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
          {seguimiento ? <TablaAvance datos={seguimiento} onAbrirFicha={abrirFicha} /> : (
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
          )}
        </TabsContent>

        <TabsContent value="alertas" className="pt-4">
          <ListaAlertas alertas={alertas} soloLectura={soloLectura} ocupada={ocupadaAlerta}
            onAsignar={(a, leccionId) => asignar.mutate({ estudianteId: a.estudiante_id, leccionId, clave: claveAlerta(a) })}
            onHabilitar={(a) => habilitarDesdeAlerta.mutate({ alerta: a, clave: claveAlerta(a) })}
            onOcultar={(a) => ocultar.mutate({ alerta: a, clave: claveAlerta(a) })}
            onAbrirFicha={(a) => abrirFicha(a.estudiante_id)} />
        </TabsContent>

        <TabsContent value="catalogo" className="pt-4">
          <CatalogoLecciones catalogo={catalogo} gradoSalon={salon.grado} soloLectura={soloLectura}
            ocupada={habilitacion.isPending ? habilitacion.variables?.leccion.id : null}
            onCambiarHabilitada={(leccion, habilitar) => habilitacion.mutate({ leccion, habilitar })}
            onAbrir={(l) => setAbierta(l.id)} />
        </TabsContent>

        <TabsContent value="estudiantes" className="pt-4">
          <PorEstudiante estudiantes={salon.estudiantes} catalogo={catalogo} asignaciones={asignaciones}
            ajustes={banco.isPending && banco.variables
              ? ajustes.map((a) => a.estudiante_id === banco.variables.estudianteId ? { ...a, banco_forzado: banco.variables.forzar } : a)
              : ajustes}
            soloLectura={soloLectura}
            onAsignar={(estudianteId, leccionId) => asignar.mutate({ estudianteId, leccionId })}
            onCerrar={(asignacionId) => cerrar.mutate(asignacionId)}
            onForzarBanco={(estudianteId, forzar) => banco.mutate({ estudianteId, forzar })} />
        </TabsContent>

        <TabsContent value="plan" className="pt-4">
          {plan ? (
            <PlanTrimestre key={JSON.stringify(plan.plan)} catalogo={catalogo} plan={plan} gradoSalon={salon.grado}
              soloLectura={soloLectura} onGuardar={guardarPlan} onDevolver={(l) => devolver.mutate(l)} />
          ) : <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
        </TabsContent>
      </Tabs>

      <Dialog open={!!leccionAbierta} onOpenChange={(o) => { if (!o) setAbierta(null); }}>
        <DialogContent className="max-h-[92vh] max-w-2xl grid-cols-[minmax(0,1fr)] overflow-y-auto">
          <DialogTitle className="sr-only">Configurar lección</DialogTitle>
          {leccionAbierta && (
            <PanelLeccion key={leccionAbierta.id} leccion={leccionAbierta} catalogo={catalogo} soloLectura={soloLectura}
              onGuardar={(c) => guardarPanel(leccionAbierta, c)} onRestaurar={() => restaurar(leccionAbierta)}
              onCerrar={() => setAbierta(null)} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
