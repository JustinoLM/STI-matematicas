/**
 * Página de colección de animaciones paso a paso del estudiante.
 *
 * Muestra hasta 10 animaciones guardadas. Cada tarjeta permite relanzar
 * la animación (re-renderiza desde los datos del problema, sin archivos).
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Clapperboard, Loader2, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { CanvasAnimationModal } from '@/components/practice/CanvasAnimationModal';
import { studentService, type AnimacionGuardadaResponse } from '@/services/studentService';
import type { Operacion } from '@/types';

// ─── Constantes ───────────────────────────────────────────────────────────────

const OPERACION_LABEL: Record<string, string> = {
  SUMA: 'Suma',
  RESTA: 'Resta',
  MULTIPLICACION: 'Multiplicación',
  DIVISION: 'División',
};

const OPERACION_COLOR: Record<string, string> = {
  SUMA: 'bg-blue-100 text-blue-800',
  RESTA: 'bg-orange-100 text-orange-800',
  MULTIPLICACION: 'bg-purple-100 text-purple-800',
  DIVISION: 'bg-green-100 text-green-800',
};

const SIMBOLO: Record<string, string> = {
  SUMA: '+',
  RESTA: '−',
  MULTIPLICACION: '×',
  DIVISION: '÷',
};

function formatFecha(isoStr: string): string {
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

// ─── Componente ───────────────────────────────────────────────────────────────

export function AnimacionesPage() {
  const queryClient = useQueryClient();
  const [animacionSeleccionada, setAnimacionSeleccionada] =
    useState<AnimacionGuardadaResponse | null>(null);
  const [eliminarId, setEliminarId] = useState<number | null>(null);

  const eliminarMutation = useMutation({
    mutationFn: (id: number) => studentService.eliminarAnimacion(id),
    onSuccess: () => {
      setEliminarId(null);
      queryClient.invalidateQueries({ queryKey: ['coleccion-animaciones'] });
    },
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ['coleccion-animaciones'],
    queryFn: () => studentService.getColeccionAnimaciones(),
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[40vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-md mx-auto mt-10 text-center text-gray-500">
        No se pudo cargar tu colección. Intenta recargar la página.
      </div>
    );
  }

  const { animaciones, total, maximo } = data;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <Clapperboard className="w-6 h-6 text-blue-600" />
            Mis Animaciones
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Guías paso a paso que guardaste durante la práctica
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          {total} / {maximo}
        </Badge>
      </div>

      {/* Barra de capacidad */}
      <div className="space-y-1">
        <Progress value={(total / maximo) * 100} className="h-2" />
        <p className="text-xs text-gray-400 text-right">
          {maximo - total} espacio{maximo - total !== 1 ? 's' : ''} disponible{maximo - total !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Lista vacía */}
      {animaciones.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-14 text-center gap-3">
            <BookOpen className="w-10 h-10 text-gray-300" />
            <p className="text-gray-500 font-medium">Aún no tienes animaciones guardadas</p>
            <p className="text-sm text-gray-400 max-w-xs">
              Cuando agotes los 3 intentos de un problema, aparecerá una guía paso a paso.
              Pulsa "Guardar" para agregarla a tu colección.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Cuadrícula de animaciones */}
      {animaciones.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {animaciones.map((anim) => (
            <Card
              key={anim.id}
              className="hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => setAnimacionSeleccionada(anim)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded ${OPERACION_COLOR[anim.operacion] ?? 'bg-gray-100 text-gray-700'}`}
                  >
                    {OPERACION_LABEL[anim.operacion] ?? anim.operacion}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    Nivel {anim.nivel_dificultad}
                  </Badge>
                </div>
                <CardTitle className="text-2xl font-mono text-center pt-2 text-gray-800 group-hover:text-blue-600 transition-colors">
                  {anim.numero1}{' '}
                  <span className="text-gray-400">{SIMBOLO[anim.operacion] ?? '?'}</span>{' '}
                  {anim.numero2}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">{formatFecha(anim.guardado_en)}</span>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs h-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        setAnimacionSeleccionada(anim);
                      }}
                    >
                      Ver pasos
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs h-7 text-red-500 hover:text-red-700 hover:border-red-300"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEliminarId(anim.id);
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modal de reproducción */}
      {animacionSeleccionada && (
        <CanvasAnimationModal
          open={!!animacionSeleccionada}
          onClose={() => setAnimacionSeleccionada(null)}
          problemaId={animacionSeleccionada.problema_id}
          operacion={animacionSeleccionada.operacion as Operacion}
          numero1={parseFloat(animacionSeleccionada.numero1)}
          numero2={parseFloat(animacionSeleccionada.numero2)}
          nivelDificultad={animacionSeleccionada.nivel_dificultad}
          onGuardar={async () => {
            // Ya está en la colección — no hacer nada
          }}
        />
      )}

      {/* Confirmación de eliminación */}
      <AlertDialog open={eliminarId !== null} onOpenChange={(v) => !v && setEliminarId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar esta animación?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará de tu colección. Si la necesitas de nuevo, deberás guardarla
              otra vez desde la práctica.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => eliminarId !== null && eliminarMutation.mutate(eliminarId)}
            >
              {eliminarMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : null}
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
