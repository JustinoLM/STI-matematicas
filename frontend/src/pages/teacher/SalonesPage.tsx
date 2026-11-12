/**
 * Salones del profesor.
 * Lista los salones del año en curso y el historial (años cerrados, de solo lectura),
 * y permite crear un salón o abrir uno existente de la organización para este año.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Users, School, Settings, Lock, Layers } from 'lucide-react';
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
import type { SalonResumen } from '@/types';

const GRADOS = [1, 2, 3, 4, 5, 6];

function SalonCard({ salon }: { salon: SalonResumen }) {
  return (
    <Card className="hover:shadow-lg transition-shadow h-full flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-xl mb-2">{salon.nombre}</CardTitle>
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="outline">{salon.grado}.º grado</Badge>
              <Badge variant="outline">{salon.anio}</Badge>
              {salon.cerrado && (
                <Badge variant="secondary" className="gap-1">
                  <Lock className="h-3 w-3" /> Cerrado
                </Badge>
              )}
            </div>
          </div>
          {!salon.cerrado && (
            <Link to={`/teacher/configuration?salon=${salon.anio_lectivo_id}`} title="Configurar práctica">
              <Button variant="ghost" size="sm">
                <Settings className="h-4 w-4" />
              </Button>
            </Link>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 flex-1 flex flex-col">
        <div className="flex items-center gap-2 text-sm">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{salon.cantidad_estudiantes}</span>
          <span className="text-muted-foreground">estudiantes</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Layers className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{salon.cantidad_grupos}</span>
          <span className="text-muted-foreground">grupos</span>
        </div>
        <div className="pt-3 border-t mt-auto">
          <Link to={`/teacher/salones/${salon.anio_lectivo_id}`}>
            <Button variant="outline" className="w-full" size="sm">
              Ver salón
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SalonesPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [nombre, setNombre] = useState('');
  const [grado, setGrado] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const { data: salones, isLoading } = useQuery({
    queryKey: ['teacher', 'salones'],
    queryFn: () => teacherService.getSalones(),
  });

  const crearMutation = useMutation({
    mutationFn: () => teacherService.crearSalon(nombre.trim(), grado),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'salones'] });
      setIsDialogOpen(false);
      setNombre('');
      setGrado(1);
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const activos = (salones ?? []).filter((s) => !s.cerrado);
  const historial = (salones ?? []).filter((s) => s.cerrado);
  const totalEstudiantes = activos.reduce((acc, s) => acc + s.cantidad_estudiantes, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Mis salones</h1>
          <p className="text-muted-foreground">
            Tus salones de este año. Los años cerrados quedan en el historial, de solo lectura.
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={(o) => { setIsDialogOpen(o); setError(null); }}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Crear salón
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear o abrir un salón</DialogTitle>
            </DialogHeader>
            <form
              onSubmit={(e) => { e.preventDefault(); if (nombre.trim()) crearMutation.mutate(); }}
              className="space-y-4"
            >
              <p className="text-sm text-muted-foreground">
                Si el salón ya existe en tu escuela (de un año anterior), se abre para este año con
                el mismo nombre y grado. Después asigna a tus estudiantes.
              </p>
              <div className="space-y-2">
                <Label htmlFor="nombre-salon">Nombre del salón</Label>
                <Input
                  id="nombre-salon"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="ej. 1A"
                  maxLength={50}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="grado-salon">Grado</Label>
                <select
                  id="grado-salon"
                  value={grado}
                  onChange={(e) => setGrado(Number(e.target.value))}
                  className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                >
                  {GRADOS.map((g) => (
                    <option key={g} value={g}>{g}.º grado</option>
                  ))}
                </select>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={crearMutation.isPending}>
                  {crearMutation.isPending ? 'Creando...' : 'Crear salón'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Salones este año</CardTitle>
            <School className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activos.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estudiantes</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalEstudiantes}</div>
            <p className="text-xs text-muted-foreground">En tus salones de este año</p>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Cargando salones...</p>
        </div>
      ) : activos.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {activos.map((s) => <SalonCard key={s.anio_lectivo_id} salon={s} />)}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <School className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No tienes salones este año</h3>
            <p className="text-muted-foreground mb-6">
              Crea tu salón y asigna a tus estudiantes. Sin salón, un estudiante no puede practicar.
            </p>
            <Button onClick={() => setIsDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Crear mi primer salón
            </Button>
          </CardContent>
        </Card>
      )}

      {historial.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Historial</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {historial.map((s) => <SalonCard key={s.anio_lectivo_id} salon={s} />)}
          </div>
        </div>
      )}
    </div>
  );
}
