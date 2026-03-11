/**
 * Gestión de desafíos del profesor.
 * Lista de desafíos activos y completados con progreso por grupo.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  Target,
  Calendar,
  Trophy,
  Users,
  CheckCircle,
  Trash2,
  Clock,
  XCircle,
  BookOpen,
  CheckSquare,
  Shield,
  Zap,
  Timer,
  Coins,
} from 'lucide-react';
import type { TipoDesafioGrupal } from '@/types';
import { teacherService } from '@/services/teacherService';
import { queryClient } from '@/lib/queryClient';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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

/** Días restantes hasta fecha límite (negativo = vencido hace N días). */
function diasRestantes(fechaLimite: string): number {
  const diff = new Date(fechaLimite).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

/** Metadatos de cada tipo de desafío. */
const TIPO_INFO: Record<TipoDesafioGrupal, {
  icono: React.ComponentType<{ className?: string }>;
  etiqueta: string;
  dificultad: number;
  dificultadLabel: string;
  dificultadColor: string;
  descripcionMeta: (obj: number, param?: number) => string;
}> = {
  problemas_resueltos: {
    icono: BookOpen,
    etiqueta: 'Resolver problemas',
    dificultad: 1,
    dificultadLabel: 'Fácil',
    dificultadColor: 'bg-green-100 text-green-700 border-green-300',
    descripcionMeta: (obj) => `${obj} problemas correctos en grupo`,
  },
  sesiones_completadas: {
    icono: CheckSquare,
    etiqueta: 'Completar prácticas',
    dificultad: 2,
    dificultadLabel: 'Medio-bajo',
    dificultadColor: 'bg-blue-100 text-blue-700 border-blue-300',
    descripcionMeta: (obj) => `${obj} prácticas completadas en grupo`,
  },
  practicas_sin_errores: {
    icono: Shield,
    etiqueta: 'Prácticas sin errores',
    dificultad: 3,
    dificultadLabel: 'Medio',
    dificultadColor: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    descripcionMeta: (obj, param) => `${obj} prácticas con máx. ${param ?? '?'} errores`,
  },
  problemas_rapidos: {
    icono: Zap,
    etiqueta: 'Problemas rápidos',
    dificultad: 4,
    dificultadLabel: 'Difícil',
    dificultadColor: 'bg-orange-100 text-orange-700 border-orange-300',
    descripcionMeta: (obj, param) => `${obj} problemas en ≤${param ?? '?'} seg/problema`,
  },
  practicas_rapidas: {
    icono: Timer,
    etiqueta: 'Prácticas en tiempo',
    dificultad: 5,
    dificultadLabel: 'Muy difícil',
    dificultadColor: 'bg-red-100 text-red-700 border-red-300',
    descripcionMeta: (obj, param) => `${obj} prácticas en ≤${param ?? '?'} minutos`,
  },
};

export function ChallengesPage() {
  const [selectedTab, setSelectedTab] = useState<'active' | 'expired' | 'completed'>('active');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [desafioToDelete, setDesafioToDelete] = useState<number | null>(null);

  // Obtener desafíos
  const { data: desafios, isLoading } = useQuery({
    queryKey: ['teacher', 'challenges'],
    queryFn: () => teacherService.getDesafios(),
  });

  // Mutation para eliminar desafío
  const eliminarDesafioMutation = useMutation({
    mutationFn: (desafioId: number) => teacherService.eliminarDesafio(desafioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'challenges'] });
      setDeleteDialogOpen(false);
      setDesafioToDelete(null);
    },
  });

  // Filtrar desafíos por tab
  const filteredDesafios = desafios?.filter((d) => {
    if (d.eliminado) return false;
    if (selectedTab === 'active') return !d.completado && !d.vencido;
    if (selectedTab === 'expired') return d.vencido && !d.completado;
    return d.completado; // 'completed'
  });

  // Contar desafíos
  const activeCount   = desafios?.filter((d) => !d.completado && !d.vencido && !d.eliminado).length || 0;
  const expiredCount  = desafios?.filter((d) => d.vencido && !d.completado && !d.eliminado).length || 0;
  const completedCount = desafios?.filter((d) => d.completado && !d.eliminado).length || 0;

  const handleDeleteClick = (desafioId: number) => {
    setDesafioToDelete(desafioId);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (desafioToDelete) {
      eliminarDesafioMutation.mutate(desafioToDelete);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Desafíos</h1>
          <p className="text-muted-foreground">
            Gestiona desafíos para motivar a tus estudiantes
          </p>
        </div>
        <Link to="/teacher/challenges/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Crear Desafío
          </Button>
        </Link>
      </div>

      {/* Estadísticas */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{desafios?.filter((d) => !d.eliminado).length || 0}</div>
            <p className="text-xs text-muted-foreground">Creados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <Target className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{activeCount}</div>
            <p className="text-xs text-muted-foreground">En progreso</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Vencidos</CardTitle>
            <XCircle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{expiredCount}</div>
            <p className="text-xs text-muted-foreground">Sin completar</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completados</CardTitle>
            <Trophy className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{completedCount}</div>
            <p className="text-xs text-muted-foreground">Logrados</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs de Filtrado */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Desafíos</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedTab} onValueChange={(v) => setSelectedTab(v as any)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="active">
                Activos ({activeCount})
              </TabsTrigger>
              <TabsTrigger value="expired">
                Vencidos ({expiredCount})
              </TabsTrigger>
              <TabsTrigger value="completed">
                Completados ({completedCount})
              </TabsTrigger>
            </TabsList>

            <TabsContent value={selectedTab} className="mt-6">
              {isLoading ? (
                <div className="text-center py-12 text-muted-foreground">
                  Cargando desafíos...
                </div>
              ) : filteredDesafios && filteredDesafios.length > 0 ? (
                <div className="space-y-4">
                  {filteredDesafios.map((desafio) => {
                    const vencido = desafio.vencido;
                    const dias = desafio.fecha_limite ? diasRestantes(desafio.fecha_limite as unknown as string) : null;

                    return (
                    <Card
                      key={desafio.id}
                      className={`hover:shadow-lg transition-shadow ${vencido ? 'border-orange-200 bg-orange-50/30' : ''}`}
                    >
                      <CardContent className="p-6">
                        {/* Header del Desafío */}
                        <div className="flex items-start justify-between mb-4">
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="text-xl font-semibold">{desafio.nombre}</h3>

                              {/* Badge de estado */}
                              {desafio.completado ? (
                                <Badge className="bg-green-100 text-green-700 border-green-300">
                                  <Trophy className="h-3 w-3 mr-1" />
                                  Completado
                                </Badge>
                              ) : vencido ? (
                                <Badge className="bg-orange-100 text-orange-700 border-orange-300">
                                  <XCircle className="h-3 w-3 mr-1" />
                                  Vencido
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-blue-600 border-blue-300">
                                  En progreso
                                </Badge>
                              )}

                              {/* Días restantes / vencido hace N días */}
                              {dias !== null && !desafio.completado && (
                                <span className={`text-xs font-medium flex items-center gap-1 ${
                                  vencido
                                    ? 'text-orange-600'
                                    : dias <= 2
                                    ? 'text-red-600'
                                    : dias <= 5
                                    ? 'text-yellow-600'
                                    : 'text-muted-foreground'
                                }`}>
                                  <Clock className="h-3 w-3" />
                                  {vencido
                                    ? `Venció hace ${Math.abs(dias)} días`
                                    : dias === 0
                                    ? '¡Vence hoy!'
                                    : `${dias} día${dias === 1 ? '' : 's'} restante${dias === 1 ? '' : 's'}`}
                                </span>
                              )}
                            </div>

                            {desafio.descripcion && (
                              <p className="text-sm text-muted-foreground">
                                {desafio.descripcion}
                              </p>
                            )}
                            {/* Tipo + dificultad */}
                            {(() => {
                              const info = TIPO_INFO[desafio.tipo as TipoDesafioGrupal];
                              if (!info) return null;
                              const TipoIcono = info.icono;
                              return (
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant="outline" className={`text-xs ${info.dificultadColor}`}>
                                    {'⭐'.repeat(info.dificultad)} {info.dificultadLabel}
                                  </Badge>
                                  <span className="flex items-center gap-1 text-sm text-muted-foreground">
                                    <TipoIcono className="h-4 w-4" />
                                    {info.descripcionMeta(desafio.objetivo_cantidad, desafio.parametro_adicional)}
                                  </span>
                                </div>
                              );
                            })()}

                            <div className="flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
                              <span className="flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                Creado: {new Date(desafio.fecha_creacion).toLocaleDateString('es-ES')}
                              </span>
                              {desafio.fecha_limite && (
                                <span className={`flex items-center gap-1 ${vencido ? 'text-orange-600 font-medium' : ''}`}>
                                  <Calendar className="h-4 w-4" />
                                  Límite: {new Date(desafio.fecha_limite).toLocaleDateString('es-ES')}
                                </span>
                              )}
                            </div>

                            {/* Recompensas */}
                            <div className="flex gap-3 flex-wrap">
                              {desafio.recompensa_puntos != null && desafio.recompensa_puntos > 0 && (
                                <div className="flex items-center gap-1.5 text-sm">
                                  <Coins className="h-4 w-4 text-yellow-500" />
                                  <span className="font-medium text-yellow-700">
                                    {desafio.recompensa_puntos.toLocaleString()} monedas por estudiante
                                  </span>
                                </div>
                              )}
                              {desafio.recompensa_texto && (
                                <div className="flex items-center gap-1.5 text-sm">
                                  <Trophy className="h-4 w-4 text-amber-500" />
                                  <span className="font-medium">{desafio.recompensa_texto}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Botón eliminar (disponible en activos y vencidos) */}
                          {!desafio.completado && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(desafio.id)}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          )}
                        </div>

                        {/* Progreso por Grupo */}
                        {desafio.progreso_grupos && desafio.progreso_grupos.length > 0 && (
                          <div className="space-y-3 border-t pt-4">
                            <h4 className="font-semibold text-sm flex items-center gap-2">
                              <Users className="h-4 w-4" />
                              Progreso por Grupo
                              {vencido && (
                                <span className="text-xs font-normal text-orange-600 ml-auto">
                                  Solo cuentan sesiones hasta la fecha límite
                                </span>
                              )}
                            </h4>
                            {desafio.progreso_grupos.map((progreso) => (
                              <div key={progreso.grupo_id} className="space-y-2">
                                <div className="flex items-center justify-between text-sm">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">{progreso.nombre_grupo}</span>
                                    {progreso.completado ? (
                                      <CheckCircle className="h-4 w-4 text-green-500" />
                                    ) : vencido ? (
                                      <XCircle className="h-4 w-4 text-orange-400" />
                                    ) : null}
                                  </div>
                                  <span className="text-muted-foreground">
                                    {progreso.progreso_actual} / {progreso.objetivo_cantidad} ({progreso.porcentaje.toFixed(0)}%)
                                  </span>
                                </div>
                                <Progress
                                  value={progreso.porcentaje}
                                  className={`h-2 ${vencido && !progreso.completado ? '[&>div]:bg-orange-400' : ''}`}
                                />
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12">
                  {selectedTab === 'active' ? (
                    <>
                      <Target className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                      <h3 className="text-lg font-semibold mb-2">No hay desafíos activos</h3>
                      <p className="text-muted-foreground mb-6">
                        Crea un desafío para motivar a tus estudiantes
                      </p>
                      <Link to="/teacher/challenges/new">
                        <Button>
                          <Plus className="mr-2 h-4 w-4" />
                          Crear Primer Desafío
                        </Button>
                      </Link>
                    </>
                  ) : selectedTab === 'expired' ? (
                    <>
                      <XCircle className="h-16 w-16 text-orange-300 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold mb-2">Sin desafíos vencidos</h3>
                      <p className="text-muted-foreground">
                        Los desafíos que expiren sin completarse aparecerán aquí
                      </p>
                    </>
                  ) : (
                    <>
                      <Trophy className="h-16 w-16 text-green-500 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold mb-2">No hay desafíos completados</h3>
                      <p className="text-muted-foreground">
                        Los desafíos completados aparecerán aquí
                      </p>
                    </>
                  )}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Dialog de Confirmación para Eliminar */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar desafío?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. El desafío será eliminado permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={eliminarDesafioMutation.isPending}
              className="bg-red-500 hover:bg-red-600"
            >
              {eliminarDesafioMutation.isPending ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
