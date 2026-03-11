/**
 * Dashboard principal del profesor.
 * Muestra resumen de grupos, alertas recientes y accesos rápidos.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Users,
  AlertTriangle,
  Target,
  Settings,
  TrendingUp,
  Award,
  Clock,
  Plus,
  Loader2,
} from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function TeacherDashboard() {
  const queryClient = useQueryClient();
  const [dialogGrupoOpen, setDialogGrupoOpen] = useState(false);
  const [nombreGrupo, setNombreGrupo] = useState('');
  const [codigoGrupo, setCodigoGrupo] = useState('');
  const [errorGrupo, setErrorGrupo] = useState<string | null>(null);

  const crearGrupoMutation = useMutation({
    mutationFn: () => teacherService.crearGrupo(nombreGrupo, codigoGrupo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'groups'] });
      setDialogGrupoOpen(false);
      setNombreGrupo('');
      setCodigoGrupo('');
      setErrorGrupo(null);
    },
    onError: (err: Error) => {
      setErrorGrupo(err.message);
    },
  });

  const handleCrearGrupo = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorGrupo(null);
    if (nombreGrupo.trim() && codigoGrupo.trim()) {
      crearGrupoMutation.mutate();
    }
  };

  // Obtener datos del dashboard
  const { data: grupos, isLoading: loadingGrupos } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: () => teacherService.getGrupos(),
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
  const totalEstudiantes = grupos?.reduce((acc, g) => acc + g.cantidad_estudiantes, 0) || 0;
  const promedioGeneral = grupos?.length
    ? grupos.reduce((acc, g) => acc + g.promedio_precision, 0) / grupos.length
    : 0;
  const alertasActivas = alertas?.filter((a) => a.activa && !a.leida).length || 0;
  const desafiosActivos = desafios?.filter((d) => !d.completado && !d.eliminado).length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard del Profesor</h1>
          <p className="text-muted-foreground">
            Resumen general de tus grupos y estudiantes
          </p>
        </div>
        <div className="flex gap-2">
          {/* Botón Crear Grupo — abre Dialog inline */}
          <Button onClick={() => setDialogGrupoOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Crear Grupo
          </Button>
          <Link to="/teacher/challenges/new">
            <Button variant="outline">
              <Target className="mr-2 h-4 w-4" />
              Nuevo Desafío
            </Button>
          </Link>
        </div>
      </div>

      {/* Dialog Crear Grupo */}
      <Dialog open={dialogGrupoOpen} onOpenChange={(open) => {
        setDialogGrupoOpen(open);
        if (!open) { setNombreGrupo(''); setCodigoGrupo(''); setErrorGrupo(null); }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear Nuevo Grupo</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCrearGrupo} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="nombre-g">Nombre del Grupo</Label>
              <Input
                id="nombre-g"
                value={nombreGrupo}
                onChange={(e) => setNombreGrupo(e.target.value)}
                placeholder="ej. 5to Grado A"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="codigo-g">Código del Grupo</Label>
              <Input
                id="codigo-g"
                value={codigoGrupo}
                onChange={(e) => setCodigoGrupo(e.target.value)}
                placeholder="ej. 5A-2024"
                required
              />
            </div>
            {errorGrupo && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                {errorGrupo}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogGrupoOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={crearGrupoMutation.isPending}>
                {crearGrupoMutation.isPending
                  ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creando...</>
                  : 'Crear Grupo'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Tarjetas de Estadísticas */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Grupos</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{grupos?.length || 0}</div>
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
              Precisión de todos los grupos
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

      {/* Resumen de Grupos */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Mis Grupos</CardTitle>
            <Link to="/teacher/groups">
              <Button variant="ghost" size="sm">
                Ver todos
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {loadingGrupos ? (
            <div className="text-center py-8 text-muted-foreground">
              Cargando grupos...
            </div>
          ) : grupos && grupos.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {grupos.slice(0, 6).map((grupo) => (
                <Link
                  key={grupo.id}
                  to={`/teacher/groups/${grupo.id}`}
                  className="block"
                >
                  <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                    <CardContent className="p-4">
                      <h3 className="font-semibold text-lg mb-2">{grupo.nombre}</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Users className="h-4 w-4" />
                          <span>{grupo.cantidad_estudiantes} estudiantes</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <TrendingUp className="h-4 w-4" />
                          <span>Promedio: {grupo.promedio_precision.toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          <span>Hoy: {grupo.problemas_resueltos_hoy} problemas</span>
                        </div>
                      </div>
                      <div className="mt-3">
                        <Badge variant="outline">{grupo.codigo_grupo}</Badge>
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
                Aún no tienes grupos creados
              </p>
              <Button onClick={() => setDialogGrupoOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Crear Primer Grupo
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Accesos Rápidos */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Link to="/teacher/groups">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardContent className="p-6 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-100">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">Gestionar Grupos</h3>
                <p className="text-sm text-muted-foreground">
                  Crear y administrar grupos
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
