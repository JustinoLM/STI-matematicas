/**
 * Notas de Regla de Tres de los estudiantes del profesor.
 */

import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, Scale } from 'lucide-react';
import { reglaDeTresService } from '@/services/reglaDeTresService';

function formatFecha(isoStr: string | null): string {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoStr;
  }
}

export function ReglaDeTresResultsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['regla-de-tres-notas-profesor'],
    queryFn: () => reglaDeTresService.obtenerNotasProfesor(),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <p className="text-muted-foreground">Cargando notas de Regla de Tres...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-muted-foreground">No se pudieron cargar las notas.</p>
      </div>
    );
  }

  const estudiantes = data?.estudiantes ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Scale className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-semibold">Regla de Tres</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Notas de tus estudiantes</CardTitle>
          <CardDescription>Última práctica de proporciones directa/inversa por estudiante</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted text-left text-xs">
                <th className="px-3 py-1.5 font-semibold">Código</th>
                <th className="px-3 py-1.5 font-semibold">Nombre</th>
                <th className="px-3 py-1.5 font-semibold">Última práctica</th>
                <th className="px-3 py-1.5 font-semibold">Correctos</th>
                <th className="px-3 py-1.5 font-semibold">Nota</th>
                <th className="px-3 py-1.5 font-semibold">Nivel</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {estudiantes.map((e) => (
                <tr key={e.estudiante_id} className="hover:bg-muted/40">
                  <td className="px-3 py-2">
                    <code className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono">
                      {e.codigo}
                    </code>
                  </td>
                  <td className="px-3 py-2 font-medium">{e.nombre_completo}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{formatFecha(e.ultima_fecha)}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {e.tiene_practica ? `${e.correctos} / ${e.total}` : '—'}
                  </td>
                  <td className="px-3 py-2">
                    {e.tiene_practica && e.nota_pct !== null ? (
                      <Badge variant={e.nota_pct >= 60 ? 'default' : 'secondary'}>
                        {e.nota_pct.toFixed(1)}%
                      </Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground italic">Sin practicar</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{e.nivel_actual ?? '—'}</td>
                </tr>
              ))}
              {estudiantes.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-xs text-muted-foreground italic">
                    No hay estudiantes asignados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
