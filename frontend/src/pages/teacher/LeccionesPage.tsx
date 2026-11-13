/**
 * Entrada "Lecciones" de la barra lateral: con un solo salón activo lleva directo a sus
 * lecciones; con varios, deja elegir el salón.
 */

import { Link, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Loader2 } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent } from '@/components/ui/card';

export default function LeccionesPage() {
  const { data: salones, isLoading } = useQuery({
    queryKey: ['teacher', 'salones'],
    queryFn: () => teacherService.getSalones(),
  });

  if (isLoading || !salones) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const activos = salones.filter((s) => !s.cerrado);
  if (activos.length === 1) {
    return <Navigate to={`/teacher/salones/${activos[0].anio_lectivo_id}/lecciones`} replace />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Lecciones</h1>
        <p className="text-sm text-muted-foreground">Elige el salón cuyas lecciones quieres preparar.</p>
      </div>
      {activos.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No tienes salones este año. <Link to="/teacher/salones" className="underline">Crea uno en Salones</Link>.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activos.map((s) => (
            <Link key={s.anio_lectivo_id} to={`/teacher/salones/${s.anio_lectivo_id}/lecciones`}>
              <Card className="transition-colors hover:border-primary">
                <CardContent className="flex items-center gap-3 p-4">
                  <BookOpen className="h-6 w-6 text-primary" />
                  <div>
                    <p className="font-semibold">Salón {s.nombre}</p>
                    <p className="text-sm text-muted-foreground">{s.grado}.º grado · {s.cantidad_estudiantes} estudiantes</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
