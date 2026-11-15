/**
 * Alertas del núcleo de todos los salones activos del profesor, para la página general de alertas.
 * Las de decimales siguen debajo, sin cambios.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { clavesProfesor, nucleoProfesorService as api } from '@/services/nucleoService';
import { ListaAlertas } from './ListaAlertas';
import { claveAlerta } from '@/lib/seguimiento';
import type { AlertaNucleo } from '@/types/nucleo';

const CONFIG_INICIAL = { signo: 'siempre', iconos: 'siempre', pistas: { 1: true, 2: true, 3: true }, prioritaria: false } as const;

export function AlertasNucleoSeccion() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { data: alertas, isLoading } = useQuery({
    queryKey: clavesProfesor.alertasProfesor,
    queryFn: () => api.alertasProfesor(),
  });

  const accion = useMutation({
    mutationFn: ({ hacer }: { hacer: () => Promise<unknown>; clave: string }) => hacer(),
    onSuccess: () => {
      setError(null);
      return Promise.all([
        qc.invalidateQueries({ queryKey: clavesProfesor.alertasProfesor }),
        qc.invalidateQueries({ queryKey: ['teacher', 'nucleo'] }),
      ]);
    },
    onError: (e: Error) => setError(e.message),
  });
  const hacer = (a: AlertaNucleo, fn: () => Promise<unknown>) => accion.mutate({ hacer: fn, clave: claveAlerta(a) });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" /> Lecciones ({alertas?.length ?? 0})
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Quién se atasca en una lección aunque tenga repaso y quién sobresale en una que todavía no está habilitada.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>}
        {isLoading || !alertas ? <p className="text-sm text-muted-foreground">Cargando…</p> : (
          <ListaAlertas alertas={alertas} mostrarSalon ocupada={accion.isPending ? accion.variables?.clave : null}
            onAsignar={(a, leccionId) => hacer(a, () => api.asignar(a.anio_lectivo_id, a.estudiante_id, leccionId))}
            onHabilitar={(a) => hacer(a, () => api.configurar(a.anio_lectivo_id, a.leccion_id, { ...CONFIG_INICIAL }))}
            onOcultar={(a) => hacer(a, () => api.ocultarAlerta(a.anio_lectivo_id, a.estudiante_id, a.leccion_id, a.tipo))}
            onAbrirFicha={(a) => navigate(`/teacher/salones/${a.anio_lectivo_id}/estudiantes/${a.estudiante_id}`)} />
        )}
      </CardContent>
    </Card>
  );
}
