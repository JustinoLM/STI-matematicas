/**
 * Página de búsqueda y listado de estudiantes.
 * Muestra todos los estudiantes de la misma organización del profesor.
 * Permite buscar por nombre o código de estudiante.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search, GraduationCap, Users, Eye, Building2, UserX } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function StudentsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [nivelFiltro, setNivelFiltro] = useState<number | null>(null);

  // Obtener estudiantes de la organización del profesor
  const { data: estudiantes, isLoading, isError } = useQuery({
    queryKey: ['teacher', 'students'],
    queryFn: () => teacherService.getEstudiantesOrg(),
    staleTime: 2 * 60 * 1000, // 2 minutos
  });

  // Filtro local por nombre, código y nivel
  const filteredStudents = (estudiantes ?? []).filter((e) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        e.nombre_completo.toLowerCase().includes(q) ||
        e.codigo_estudiante.toLowerCase().includes(q);
      if (!matchesSearch) return false;
    }
    if (nivelFiltro !== null && e.nivel_actual !== nivelFiltro) return false;
    return true;
  });

  const totalActivos = estudiantes?.filter((e) => e.activo).length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Estudiantes</h1>
        <p className="text-muted-foreground">
          Estudiantes de tu organización que puedes asignar a grupos
        </p>
      </div>

      {/* Buscador y Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre o código de estudiante..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            {/* Filtro por nivel */}
            <select
              value={nivelFiltro ?? ''}
              onChange={(e) => setNivelFiltro(e.target.value ? parseInt(e.target.value) : null)}
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="">Todos los niveles</option>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>Nivel {n}</option>
              ))}
            </select>
            {(searchQuery || nivelFiltro !== null) && (
              <Button variant="outline" onClick={() => { setSearchQuery(''); setNivelFiltro(null); }}>
                Limpiar filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Estadísticas */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total en Organización</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{estudiantes?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground">Estudiantes registrados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalActivos}</div>
            <p className="text-xs text-muted-foreground">Con cuenta activa</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {searchQuery ? 'Resultados' : 'Mostrando'}
            </CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredStudents.length}</div>
            <p className="text-xs text-muted-foreground">
              {searchQuery ? 'Coincidencias encontradas' : 'Todos los estudiantes'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabla de Estudiantes */}
      <Card>
        <CardHeader>
          <CardTitle>
            {searchQuery
              ? `Resultados para "${searchQuery}"`
              : 'Todos los Estudiantes'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground">
              Cargando estudiantes...
            </div>
          ) : isError ? (
            <div className="text-center py-12">
              <UserX className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Error al cargar estudiantes</h3>
              <p className="text-muted-foreground">
                Verifica tu conexión e intenta de nuevo.
              </p>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="text-center py-12">
              <GraduationCap className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                {searchQuery
                  ? 'No se encontraron resultados'
                  : 'No hay estudiantes en tu organización'}
              </h3>
              <p className="text-muted-foreground">
                {searchQuery
                  ? 'Intenta con otro término de búsqueda'
                  : 'Pide al administrador que asigne estudiantes a tu organización'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold">Código</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold">Nivel</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold">Precisión</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">Estado</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredStudents.map((student) => {
                    const nivel = student.nivel_actual ?? 1;
                    const precision = student.precision_ultimos_15 ?? 0;
                    return (
                      <tr key={student.id} className="hover:bg-muted/50">
                        <td className="px-4 py-3">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {student.codigo_estudiante}
                          </code>
                        </td>
                        <td className="px-4 py-3 font-medium">{student.nombre_completo}</td>
                        <td className="px-4 py-3 text-center">
                          <Badge variant="outline">Nivel {nivel}</Badge>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-sm font-semibold ${
                            precision >= 80 ? 'text-green-600' :
                            precision >= 50 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {precision.toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={student.activo ? 'default' : 'secondary'}>
                            {student.activo ? 'Activo' : 'Inactivo'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link to={`/teacher/students/${student.id}`}>
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4 mr-2" />
                              Ver Detalle
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Nota informativa */}
      {!isLoading && !isError && (estudiantes?.length ?? 0) > 0 && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <Users className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-800">
                <span className="font-medium">¿Cómo agregar estudiantes a un grupo en bulk?</span>
                <span className="text-blue-700">
                  {' '}Ve al detalle de un grupo y usa el tab "Importar" para subir una lista de códigos en CSV o Excel.
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
