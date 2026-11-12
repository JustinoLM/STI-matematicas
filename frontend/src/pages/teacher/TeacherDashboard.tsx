/**
 * Dashboard principal del profesor.
 * Muestra resumen de los salones del año, alertas recientes y accesos rápidos.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Users,
  AlertTriangle,
  Target,
  Settings,
  TrendingUp,
  Award,
  Plus,
  Layers,
} from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function TeacherDashboard() {
  // Salones del año en curso
  const { data: todosLosSalones, isLoading: loadingSalones } = useQuery({
    queryKey: ['teacher', 'salones'],
    queryFn: () => teacherService.getSalones(),
  });
  const salones = (todosLosSalones ?? []).filter((s) => !s.cerrado);

  const { data: estudiantes } = useQuery({
    queryKey: ['teacher', 'students'],
    queryFn: () => teacherService.getEstudiantesOrg(),
    staleTime: 2 * 60 * 1000,
  });

  const { data: alertas, isLoading: loadingAlertas } = useQuery({
    queryKey: ['teacher', 'alerts'],
    queryFn: () => teacherService.getAlertas(),
  });

  const { data: desafios } = useQuery({
    queryKey: ['teacher', 'challenges'],
    queryFn: () => teacherService.getDesafios(),
  });

  // Calcular estadísticas generales
  const totalEstudiantes = salones.reduce((acc, s) => acc + s.cantidad_estudiantes, 0);
  const promedioGeneral = estudiantes?.length
    ? estudiantes.reduce((acc, e) => acc + e.precision_ultimos_15, 0) / estudiantes.length
    : 0;
  const alertasActivas = alertas?.filter((a) => a.activa && !a.leida).length || 0;
  const desafiosActivos = desafios?.filter((d) => d.estado === 'activo' && !d.eliminado).length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard del Profesor</h1>
          <p className="text-muted-foreground">
            Resumen de tus salones y estudiantes de este año
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/teacher/salones">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Mis salones
            </Button>
          </Link>
          <Link to="/teacher/challenges/new">
            <Button variant="outline">
              <Target className="mr-2 h-4 w-4" />
              Nuevo Desafío
            </Button>
          </Link>
        </div>
      </div>

      {/* Tarjetas de Estadísticas */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Salones este año</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{salones.length}</div>
            <p className="text-xs text-muted-foreground">
              {totalEstudiantes} estudiantes en total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promedio General</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{promedioGeneral.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              Precisión de tus estudiantes
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alertas Activas</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{alertasActivas}</div>
            <p className="text-xs text-muted-foreground">
              Requieren atención
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Desafíos Activos</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{desafiosActivos}</div>
            <p className="text-xs text-muted-foreground">
              En progreso
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alertas Recientes */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Alertas Recientes</CardTitle>
            <Link to="/teacher/alerts">
              <Button variant="ghost" size="sm">
                Ver todas
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {loadingAlertas ? (
            <div className="text-center py-8 text-muted-foreground">
              Cargando alertas...
            </div>
          ) : alertas && alertas.length > 0 ? (
            <div className="space-y-3">
              {alertas.slice(0, 5).map((alerta) => (
                <div
                  key={alerta.id}
                  className="flex items-start gap-3 rounded-lg border p-3"
                >
                  <AlertTriangle
                    className={`h-5 w-5 mt-0.5 ${
                      alerta.severidad === 'alta'
                        ? 'text-red-500'
                        : alerta.severidad === 'media'
                        ? 'text-yellow-500'
                        : 'text-blue-500'
                    }`}
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{alerta.titulo}</p>
                      <Badge
                        variant={
                          alerta.severidad === 'alta'
                            ? 'destructive'
                            : alerta.severidad === 'media'
                            ? 'default'
                            : 'secondary'
                        }
                      >
                        {alerta.severidad}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{alerta.mensaje}</p>
                    <p className="text-xs text-muted-foreground">
                      {alerta.nombre_estudiante} ({alerta.codigo_estudiante})
                    </p>
                  </div>
                  <Link to={`/teacher/students/${alerta.estudiante_id}`}>
                    <Button variant="ghost" size="sm">
                      Ver detalle
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Award className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground">
                ¡No hay alertas activas! Todo está funcionando correctamente.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Resumen de salones */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Mis salones</CardTitle>
            <Link to="/teacher/salones">
              <Button variant="ghost" size="sm">
                Ver todos
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {loadingSalones ? (
            <div className="text-center py-8 text-muted-foreground">
              Cargando salones...
            </div>
          ) : salones.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {salones.slice(0, 6).map((salon) => (
                <Link key={salon.anio_lectivo_id} to={`/teacher/salones/${salon.anio_lectivo_id}`} className="block">
                  <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                    <CardContent className="p-4">
                      <h3 className="font-semibold text-lg mb-2">{salon.nombre}</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Users className="h-4 w-4" />
                          <span>{salon.cantidad_estudiantes} estudiantes</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Layers className="h-4 w-4" />
                          <span>{salon.cantidad_grupos} grupos</span>
                        </div>
                      </div>
                      <div className="mt-3">
                        <Badge variant="outline">{salon.grado}.º grado</Badge>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground mb-4">
                Aún no tienes salones este año
              </p>
              <Link to="/teacher/salones">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Crear mi salón
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Accesos Rápidos */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link to="/teacher/salones">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-100">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">Mis salones</h3>
                <p className="text-sm text-muted-foreground">
                  Estudiantes, grupos y trimestres
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/teacher/students">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-purple-100">
                <Award className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h3 className="font-semibold">Ver Estudiantes</h3>
                <p className="text-sm text-muted-foreground">
                  Buscar y monitorear
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/teacher/challenges">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-green-100">
                <Target className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold">Desafíos</h3>
                <p className="text-sm text-muted-foreground">
                  Crear y gestionar desafíos
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/teacher/configuration">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-orange-100">
                <Settings className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <h3 className="font-semibold">Configuración</h3>
                <p className="text-sm text-muted-foreground">
                  Ajustar parámetros
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
