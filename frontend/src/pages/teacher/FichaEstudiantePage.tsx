/**
 * Ficha del estudiante en el núcleo (fase 6b), dentro de un año lectivo del profesor.
 * La práctica de decimales tiene su propia pantalla (StudentDetailPage); las dos se enlazan.
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FichaEstudiante } from '@/components/teacher/seguimiento/FichaEstudiante';
import { clavesProfesor, nucleoProfesorService as api } from '@/services/nucleoService';

export default function FichaEstudiantePage() {
  const { id, estudianteId } = useParams<{ id: string; estudianteId: string }>();
  const anioId = parseInt(id || '0');
  const estId = parseInt(estudianteId || '0');
  const [trimestre, setTrimestre] = useState<number | null>(null);

  const { data: ficha, isLoading, error, isFetching } = useQuery({
    queryKey: clavesProfesor.ficha(anioId, estId, trimestre),
    queryFn: () => api.ficha(anioId, estId, trimestre),
    enabled: !!anioId && !!estId,
    placeholderData: (previo) => previo,
  });

  if (isLoading) {
    return <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>;
  }
  if (error || !ficha) {
    return (
      <div className="space-y-4 py-12 text-center">
        <p className="text-muted-foreground">{error instanceof Error ? error.message : 'No se encontró la ficha.'}</p>
        <Link to={`/teacher/salones/${anioId}/lecciones`} className="underline">Volver al salón</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link to={`/teacher/salones/${anioId}/lecciones?pestana=avance`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="mr-1 h-4 w-4" /> Avance del salón {ficha.salon.nombre}
        </Link>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">{ficha.estudiante.nombre}</h1>
            <p className="text-sm text-muted-foreground">
              {ficha.estudiante.codigo} · Salón {ficha.salon.nombre} ({ficha.salon.grado}.º) · {ficha.salon.anio}
            </p>
          </div>
          <Link to={`/teacher/students/${ficha.estudiante.id}`} className="text-sm underline-offset-2 hover:underline">
            Práctica de decimales →
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Periodo">
        <span className="mr-1 text-sm text-muted-foreground">Periodo:</span>
        {[null, 1, 2, 3].map((t) => (
          <Button key={t ?? 'hoy'} size="sm" variant={trimestre === t ? 'default' : 'outline'} aria-pressed={trimestre === t}
            className="min-h-[40px] min-w-[52px]" onClick={() => setTrimestre(t)}>
            {t === null ? 'Hoy' : `T${t}`}
          </Button>
        ))}
        {isFetching && <Loader2 className="ml-2 h-4 w-4 animate-spin text-muted-foreground" />}
      </div>

      <FichaEstudiante ficha={ficha} />
    </div>
  );
}
