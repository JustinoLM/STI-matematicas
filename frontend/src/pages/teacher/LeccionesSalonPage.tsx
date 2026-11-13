/**
 * Lecciones del salón (núcleo, fase 6a): catálogo para habilitar y configurar lecciones, sus
 * prerrequisitos en este año, y los ajustes por estudiante (asignaciones y banco forzado).
 * Un año cerrado se muestra en solo lectura.
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Lock, Star } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { clavesProfesor, nucleoProfesorService as api } from '@/services/nucleoService';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CatalogoLecciones } from '@/components/teacher/lecciones/CatalogoLecciones';
import { PanelLeccion } from '@/components/teacher/lecciones/PanelLeccion';
import { PorEstudiante } from '@/components/teacher/lecciones/PorEstudiante';
import { MAX_PRIORITARIAS, configDe, prioritarias } from '@/lib/leccionesSalon';
import type { ConfigLeccion, LeccionSalon } from '@/types/nucleo';

export default function LeccionesSalonPage() {
  const { id } = useParams<{ id: string }>();
  const anioId = parseInt(id || '0');
  const qc = useQueryClient();
  const [abierta, setAbierta] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const refrescar = (...claves: (readonly unknown[])[]) => {
    for (const k of claves) qc.invalidateQueries({ queryKey: k });
  };
  const alFallar = (e: Error) => setError(e.message);

  const habilitacion = useMutation({
    mutationFn: ({ leccion, habilitar }: { leccion: LeccionSalon; habilitar: boolean }) =>
      habilitar
        ? api.configurar(anioId, leccion.id, { ...configDe(leccion), prioritaria: false })
        : api.deshabilitar(anioId, leccion.id),
    // Se espera la recarga del catálogo para que el interruptor no vuelva atrás un instante
    onSuccess: () => { setError(null); return qc.invalidateQueries({ queryKey: clavesProfesor.catalogo(anioId) }); },
    onError: alFallar,
  });
  const asignar = useMutation({
    mutationFn: ({ estudianteId, leccionId }: { estudianteId: number; leccionId: string }) =>
      api.asignar(anioId, estudianteId, leccionId),
    onSuccess: () => { setError(null); refrescar(clavesProfesor.asignaciones(anioId)); },
    onError: alFallar,
  });
  const cerrar = useMutation({
    mutationFn: (asignacionId: number) => api.cerrarAsignacion(asignacionId),
    onSuccess: () => { setError(null); refrescar(clavesProfesor.asignaciones(anioId)); },
    onError: alFallar,
  });
  const banco = useMutation({
    mutationFn: ({ estudianteId, forzar }: { estudianteId: number; forzar: boolean }) =>
      api.forzarBanco(anioId, estudianteId, forzar),
    onSuccess: () => { setError(null); return qc.invalidateQueries({ queryKey: clavesProfesor.ajustes(anioId) }); },
    onError: alFallar,
  });

  const guardarPanel = async (leccion: LeccionSalon, cambios: { config: ConfigLeccion | null; prerrequisitos: string[] | null }) => {
    try {
      if (cambios.config) await api.configurar(anioId, leccion.id, cambios.config);
      if (cambios.prerrequisitos) await api.editarPrerrequisitos(anioId, leccion.id, cambios.prerrequisitos);
    } finally {
      refrescar(clavesProfesor.catalogo(anioId));
    }
  };
  const restaurar = async (leccion: LeccionSalon) => {
    await api.restaurarPrerrequisitos(anioId, leccion.id);
    refrescar(clavesProfesor.catalogo(anioId));
  };

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
              Elige qué practica el salón y cómo. Una lección queda habilitada hasta que la desactives.
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

      <Tabs defaultValue="catalogo">
        <TabsList className="grid w-full grid-cols-2 sm:w-auto sm:inline-grid">
          <TabsTrigger value="catalogo">Catálogo</TabsTrigger>
          <TabsTrigger value="estudiantes">Por estudiante</TabsTrigger>
        </TabsList>
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
