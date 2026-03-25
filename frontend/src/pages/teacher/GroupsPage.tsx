/**
 * Página de gestión de grupos del profesor.
 * Lista todos los grupos con opciones para crear, editar y ver detalles.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Users, TrendingUp, Clock, Settings, Trash2, Check, X, Loader2 } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { queryClient } from '@/lib/queryClient';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function GroupsPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [nombreGrupo, setNombreGrupo] = useState('');
  const [codigoGrupo, setCodigoGrupo] = useState('');
  const [confirmarBorrarId, setConfirmarBorrarId] = useState<number | null>(null);

  // Obtener grupos
  const { data: grupos, isLoading } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: () => teacherService.getGrupos(),
  });

  // Total de estudiantes únicos en la organización (evita contar duplicados entre grupos)
  const { data: estudiantesOrg } = useQuery({
    queryKey: ['teacher', 'students'],
    queryFn: () => teacherService.getEstudiantesOrg(),
    staleTime: 2 * 60 * 1000,
  });

  // Mutation para crear grupo
  const crearGrupoMutation = useMutation({
    mutationFn: () => teacherService.crearGrupo(nombreGrupo, codigoGrupo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'groups'] });
      setIsDialogOpen(false);
      setNombreGrupo('');
      setCodigoGrupo('');
    },
  });

  // Mutation para eliminar grupo
  const eliminarGrupoMutation = useMutation({
    mutationFn: (grupoId: number) => teacherService.eliminarGrupo(grupoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'groups'] });
      setConfirmarBorrarId(null);
    },
  });

  const handleCrearGrupo = (e: React.FormEvent) => {
    e.preventDefault();
    if (nombreGrupo && codigoGrupo) {
      crearGrupoMutation.mutate();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Mis Grupos</h1>
          <p className="text-muted-foreground">
            Gestiona tus grupos y estudiantes
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Crear Grupo
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear Nuevo Grupo</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCrearGrupo} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre del Grupo</Label>
                <Input
                  id="nombre"
                  value={nombreGrupo}
                  onChange={(e) => setNombreGrupo(e.target.value)}
                  placeholder="ej. 5to Grado A"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="codigo">Código del Grupo</Label>
                <Input
                  id="codigo"
                  value={codigoGrupo}
                  onChange={(e) => setCodigoGrupo(e.target.value)}
                  placeholder="ej. 5A-2024"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={crearGrupoMutation.isPending}>
                  {crearGrupoMutation.isPending ? 'Creando...' : 'Crear Grupo'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Estadísticas Generales */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Grupos</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{grupos?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Grupos activos</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Estudiantes</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {estudiantesOrg?.length ?? 0}
            </div>
            <p className="text-xs text-muted-foreground">En tu organización</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promedio General</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {grupos?.length
                ? (
                    grupos.reduce((acc, g) => acc + g.promedio_precision, 0) /
                    grupos.length
                  ).toFixed(1)
                : 0}
              %
            </div>
            <p className="text-xs text-muted-foreground">Precisión promedio</p>
          </CardContent>
        </Card>
      </div>

      {/* Lista de Grupos */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando grupos...</p>
        </div>
      ) : grupos && grupos.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {grupos.map((grupo) => (
            <Card key={grupo.id} className="hover:shadow-lg transition-shadow h-full flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">{grupo.nombre}</CardTitle>
                    <Badge variant="outline">{grupo.codigo_grupo}</Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <Link
                      to={`/teacher/configuration?grupo=${grupo.id}`}
                    >
                      <Button variant="ghost" size="sm">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-400 hover:text-red-600 hover:bg-red-50"
                      onClick={() => setConfirmarBorrarId(grupo.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3 flex-1 flex flex-col">
                <div className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{grupo.cantidad_estudiantes}</span>
                  <span className="text-muted-foreground">estudiantes</span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">
                    {grupo.promedio_precision.toFixed(1)}%
                  </span>
                  <span className="text-muted-foreground">precisión promedio</span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{grupo.problemas_resueltos_hoy}</span>
                  <span className="text-muted-foreground">problemas hoy</span>
                </div>

                <div className="pt-3 border-t mt-auto">
                  {confirmarBorrarId === grupo.id ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-red-600 font-medium flex-1">¿Eliminar este grupo?</span>
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={eliminarGrupoMutation.isPending}
                        onClick={() => eliminarGrupoMutation.mutate(grupo.id)}
                      >
                        {eliminarGrupoMutation.isPending
                          ? <Loader2 className="h-3 w-3 animate-spin" />
                          : <Check className="h-3 w-3" />}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setConfirmarBorrarId(null)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ) : (
                    <Link to={`/teacher/groups/${grupo.id}`}>
                      <Button variant="outline" className="w-full" size="sm">
                        Ver Detalle
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <Users className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No hay grupos creados</h3>
            <p className="text-muted-foreground mb-6">
              Crea tu primer grupo para comenzar a gestionar estudiantes
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Crear Primer Grupo
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
