/**
 * Página de detalle de un grupo específico.
 * Muestra estadísticas, gestión de estudiantes (agregar/quitar) y borrar grupo.
 */

import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Users,
  TrendingUp,
  Clock,
  AlertTriangle,
  Award,
  BarChart3,
  UserPlus,
  UserMinus,
  Search,
  Trash2,
  Check,
  X,
  Loader2,
  Eye,
} from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function GroupDetailPage() {
  const { id } = useParams<{ id: string }>();
  const grupoId = parseInt(id || '0');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [busqueda, setBusqueda] = useState('');
  const [confirmarBorrar, setConfirmarBorrar] = useState(false);

  // ── Queries ──────────────────────────────────────────────────────────────
  const { data: grupo, isLoading: loadingGrupo } = useQuery({
    queryKey: ['teacher', 'group', grupoId],
    queryFn: () => teacherService.getGrupoDetalle(grupoId),
    enabled: !!grupoId,
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['teacher', 'group', grupoId, 'statistics'],
    queryFn: () => teacherService.getEstadisticasGrupo(grupoId),
    enabled: !!grupoId,
  });

  // Todos los estudiantes de la organización
  const { data: estudiantesOrg = [] } = useQuery({
    queryKey: ['teacher', 'estudiantes-org'],
    queryFn: () => teacherService.getEstudiantesOrg(),
    enabled: !!grupoId,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const agregarMutation = useMutation({
    mutationFn: (estudianteId: number) =>
      teacherService.agregarEstudiante(grupoId, estudianteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'group', grupoId] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'group', grupoId, 'statistics'] });
    },
  });

  const quitarMutation = useMutation({
    mutationFn: (estudianteId: number) =>
      teacherService.removerEstudiante(grupoId, estudianteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'group', grupoId] });
      queryClient.invalidateQueries({ queryKey: ['teacher', 'group', grupoId, 'statistics'] });
    },
  });

  const eliminarGrupoMutation = useMutation({
    mutationFn: () => teacherService.eliminarGrupo(grupoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'groups'] });
      navigate('/teacher/groups');
    },
  });

  // ── Derivados ─────────────────────────────────────────────────────────────
  // IDs de estudiantes ya en el grupo
  const idsEnGrupo = new Set(
    (grupo?.estudiantes ?? []).map((e: any) => e.estudiante_id)
  );

  // Estudiantes disponibles (no están en el grupo) con filtro de búsqueda
  const estudiantesDisponibles = estudiantesOrg.filter((e) => {
    if (idsEnGrupo.has(e.id)) return false;
    if (!busqueda) return true;
    const q = busqueda.toLowerCase();
    return (
      e.nombre_completo.toLowerCase().includes(q) ||
      e.codigo_estudiante.toLowerCase().includes(q)
    );
  });

  // ── Carga ─────────────────────────────────────────────────────────────────
  if (loadingGrupo || loadingStats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <p className="text-muted-foreground">Cargando información del grupo...</p>
      </div>
    );
  }

  if (!grupo) {
    return (
      <div className="space-y-6">
        <Link to="/teacher/groups">
          <Button variant="ghost">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Grupos
          </Button>
        </Link>
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">Grupo no encontrado</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <Link to="/teacher/groups">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a Grupos
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">{grupo.nombre}</h1>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{grupo.codigo_grupo}</Badge>
            <Badge variant={grupo.activo ? 'default' : 'secondary'}>
              {grupo.activo ? 'Activo' : 'Inactivo'}
            </Badge>
          </div>
        </div>

        {/* Botón borrar grupo */}
        <div className="flex items-center gap-2">
          <Link to={`/teacher/configuration?grupo=${grupoId}`}>
            <Button variant="outline">Configurar Práctica</Button>
          </Link>

          {confirmarBorrar ? (
            <div className="flex items-center gap-2 border border-red-200 bg-red-50 rounded-lg px-3 py-2">
              <span className="text-sm text-red-700 font-medium">¿Eliminar grupo?</span>
              <Button
                size="sm"
                variant="destructive"
                disabled={eliminarGrupoMutation.isPending}
                onClick={() => eliminarGrupoMutation.mutate()}
              >
                {eliminarGrupoMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Check className="h-3 w-3" />
                )}
                Sí, eliminar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmarBorrar(false)}
              >
                <X className="h-3 w-3" />
                Cancelar
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="text-red-500 hover:text-red-700 hover:bg-red-50"
              onClick={() => setConfirmarBorrar(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Eliminar grupo
            </Button>
          )}
        </div>
      </div>

      {/* ── Estadísticas Principales ────────────────────────────────────── */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Estudiantes</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_estudiantes}</div>
              <p className="text-xs text-muted-foreground">
                {stats.estudiantes_activos} activos
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Precisión Promedio</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.promedio_precision.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">Del grupo</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Problemas Resueltos</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.problemas_resueltos_hoy}</div>
              <p className="text-xs text-muted-foreground">
                Hoy • {stats.problemas_resueltos_total} total
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Velocidad Promedio</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.promedio_velocidad.toFixed(1)}s</div>
              <p className="text-xs text-muted-foreground">Por problema</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Gestión de Estudiantes con Tabs ─────────────────────────────── */}
      <Tabs defaultValue="estudiantes">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="estudiantes">
            <Users className="mr-2 h-4 w-4" />
            Estudiantes ({(grupo.estudiantes ?? []).length})
          </TabsTrigger>
          <TabsTrigger value="agregar">
            <UserPlus className="mr-2 h-4 w-4" />
            Agregar estudiantes
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Estudiantes actuales del grupo */}
        <TabsContent value="estudiantes">
          <Card>
            <CardContent className="pt-4">
              {(grupo.estudiantes ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-10">
                  No hay estudiantes en este grupo aún. Usa la pestaña "Agregar estudiantes".
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                        <th className="px-4 py-3 text-center text-sm font-semibold">Nivel</th>
                        <th className="px-4 py-3 text-center text-sm font-semibold">Precisión</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold">Acciones</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {(grupo.estudiantes as any[]).map((est) => (
                        <tr key={est.estudiante_id} className="hover:bg-muted/50">
                          <td className="px-4 py-3">
                            <code className="text-xs bg-muted px-2 py-1 rounded">
                              {est.codigo_estudiante}
                            </code>
                          </td>
                          <td className="px-4 py-3 font-medium">{est.nombre_completo}</td>
                          <td className="px-4 py-3 text-center">
                            <Badge variant="outline">Nivel {est.nivel_actual}</Badge>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-sm font-semibold ${
                              est.precision_ultimos_15 >= 80 ? 'text-green-600' :
                              est.precision_ultimos_15 >= 50 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {est.precision_ultimos_15.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Link to={`/teacher/students/${est.estudiante_id}`}>
                                <Button size="sm" variant="ghost">
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                disabled={quitarMutation.isPending}
                                onClick={() => quitarMutation.mutate(est.estudiante_id)}
                              >
                                {quitarMutation.isPending ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <UserMinus className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Agregar estudiantes */}
        <TabsContent value="agregar">
          <Card>
            <CardContent className="pt-4 space-y-3">
              {/* Buscador */}
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Buscar por nombre o código..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              {estudiantesOrg.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  No hay estudiantes en tu organización.
                </p>
              ) : estudiantesDisponibles.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {busqueda
                    ? 'No se encontraron estudiantes con esa búsqueda.'
                    : 'Todos los estudiantes ya están en el grupo.'}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-muted">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold">Agregar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {estudiantesDisponibles.map((est) => (
                        <tr key={est.id} className="hover:bg-muted/50">
                          <td className="px-4 py-3">
                            <code className="text-xs bg-muted px-2 py-1 rounded">
                              {est.codigo_estudiante}
                            </code>
                          </td>
                          <td className="px-4 py-3 font-medium">{est.nombre_completo}</td>
                          <td className="px-4 py-3 text-right">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-green-600 hover:text-green-800 hover:bg-green-50"
                              disabled={agregarMutation.isPending}
                              onClick={() => agregarMutation.mutate(est.id)}
                            >
                              {agregarMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <UserPlus className="h-4 w-4 mr-1" />
                              )}
                              Agregar
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Alertas y Clasificación ─────────────────────────────────────── */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="h-5 w-5" />
                Rezagados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.estudiantes_rezagados}</div>
              <p className="text-sm text-muted-foreground mt-1">Precisión menor a 50%</p>
              {stats.estudiantes_rezagados > 0 && (
                <Link to="/teacher/alerts">
                  <Button variant="link" className="px-0 mt-2">Ver alertas</Button>
                </Link>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-yellow-600">
                <Clock className="h-5 w-5" />
                Estancados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.estudiantes_estancados}</div>
              <p className="text-sm text-muted-foreground mt-1">Mucho tiempo en mismo nivel</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-600">
                <Award className="h-5 w-5" />
                Sobresalientes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.estudiantes_sobresalientes}</div>
              <p className="text-sm text-muted-foreground mt-1">Precisión mayor a 90%</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Distribución por Niveles ────────────────────────────────────── */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>Distribución por Niveles</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[1, 2, 3, 4, 5].map((nivel) => {
              const cantidad = stats.distribucion_niveles[nivel] || 0;
              const porcentaje = stats.total_estudiantes
                ? (cantidad / stats.total_estudiantes) * 100
                : 0;

              return (
                <div key={nivel} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">Nivel {nivel}</span>
                    <span className="text-muted-foreground">
                      {cantidad} estudiantes ({porcentaje.toFixed(0)}%)
                    </span>
                  </div>
                  <Progress value={porcentaje} className="h-2" />
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* ── Actividad del Grupo ─────────────────────────────────────────── */}
      {stats && stats.total_estudiantes > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Actividad del Grupo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-sm font-medium">Estudiantes Activos (últimos 7 días)</p>
                <div className="flex items-center gap-2">
                  <div className="text-3xl font-bold">{stats.estudiantes_activos}</div>
                  <div className="text-sm text-muted-foreground">de {stats.total_estudiantes}</div>
                </div>
                <Progress
                  value={(stats.estudiantes_activos / stats.total_estudiantes) * 100}
                  className="h-2"
                />
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Estudiantes Inactivos</p>
                <div className="flex items-center gap-2">
                  <div className="text-3xl font-bold">{stats.estudiantes_inactivos}</div>
                  <div className="text-sm text-muted-foreground">sin actividad reciente</div>
                </div>
                {stats.estudiantes_inactivos > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Considera contactar a estos estudiantes
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Acciones Rápidas ────────────────────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-2">
        <Link to="/teacher/students">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-100">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">Ver Todos los Estudiantes</h3>
                <p className="text-sm text-muted-foreground">Historial y progreso individual</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to={`/teacher/challenges/new?grupo=${grupoId}`}>
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-green-100">
                <Award className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold">Crear Desafío</h3>
                <p className="text-sm text-muted-foreground">Nuevo desafío para este grupo</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
