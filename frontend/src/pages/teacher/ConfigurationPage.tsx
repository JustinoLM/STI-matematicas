/**
 * Configuración de prácticas por grupo.
 * Permite al profesor configurar restricciones de práctica para grupos específicos.
 */

import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Settings, Save, AlertCircle } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { queryClient } from '@/lib/queryClient';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function ConfigurationPage() {
  const [searchParams] = useSearchParams();
  const grupoIdParam = searchParams.get('grupo');

  // State del formulario
  const [grupoId, setGrupoId] = useState<number | null>(
    grupoIdParam ? parseInt(grupoIdParam) : null
  );
  const [operacionesPermitidas, setOperacionesPermitidas] = useState<string[]>([
    'suma',
    'resta',
    'multiplicacion',
    'division',
  ]);
  const [nivelesPermitidos, setNivelesPermitidos] = useState<number[]>([1, 2, 3, 4, 5]);
  const [rangoMin, setRangoMin] = useState('0');
  const [rangoMax, setRangoMax] = useState('100');
  const [decimalesMaximos, setDecimalesMaximos] = useState('2');
  const [pistasHabilitadas, setPistasHabilitadas] = useState<Record<string, boolean>>({
    nivel_1: true,
    nivel_2: true,
    nivel_3: true,
  });

  // Obtener grupos
  const { data: grupos } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: () => teacherService.getGrupos(),
  });

  // Obtener configuración actual del grupo
  const { data: configuracionActual } = useQuery({
    queryKey: ['teacher', 'group', grupoId, 'configuration'],
    queryFn: () => teacherService.getConfiguracionGrupo(grupoId!),
    enabled: !!grupoId,
  });

  // Cargar configuración actual si existe
  useEffect(() => {
    if (configuracionActual) {
      setOperacionesPermitidas(configuracionActual.operaciones_permitidas);
      setNivelesPermitidos(configuracionActual.niveles_permitidos);
      setRangoMin(configuracionActual.rango_min.toString());
      setRangoMax(configuracionActual.rango_max.toString());
      setDecimalesMaximos(configuracionActual.decimales_maximos.toString());
      setPistasHabilitadas(configuracionActual.pistas_habilitadas);
    }
  }, [configuracionActual]);

  // Mutation para crear configuración
  const crearConfiguracionMutation = useMutation({
    mutationFn: (data: {
      grupo_id: number;
      operaciones_permitidas: string[];
      niveles_permitidos: number[];
      rango_min: number;
      rango_max: number;
      decimales_maximos: number;
      pistas_habilitadas: Record<string, boolean>;
    }) => teacherService.crearConfiguracion(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'group', grupoId, 'configuration'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!grupoId) return;

    crearConfiguracionMutation.mutate({
      grupo_id: grupoId,
      operaciones_permitidas: operacionesPermitidas,
      niveles_permitidos: nivelesPermitidos,
      rango_min: parseFloat(rangoMin),
      rango_max: parseFloat(rangoMax),
      decimales_maximos: parseInt(decimalesMaximos),
      pistas_habilitadas: pistasHabilitadas,
    });
  };

  const toggleOperacion = (operacion: string) => {
    if (operacionesPermitidas.includes(operacion)) {
      setOperacionesPermitidas(operacionesPermitidas.filter((op) => op !== operacion));
    } else {
      setOperacionesPermitidas([...operacionesPermitidas, operacion]);
    }
  };

  const toggleNivel = (nivel: number) => {
    if (nivelesPermitidos.includes(nivel)) {
      setNivelesPermitidos(nivelesPermitidos.filter((n) => n !== nivel));
    } else {
      setNivelesPermitidos([...nivelesPermitidos, nivel]);
    }
  };

  const togglePista = (nivel: string) => {
    setPistasHabilitadas({
      ...pistasHabilitadas,
      [nivel]: !pistasHabilitadas[nivel],
    });
  };

  const operaciones = [
    { id: 'suma', nombre: 'Suma' },
    { id: 'resta', nombre: 'Resta' },
    { id: 'multiplicacion', nombre: 'Multiplicación' },
    { id: 'division', nombre: 'División' },
  ];

  const niveles = [1, 2, 3, 4, 5];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Configuración de Práctica</h1>
        <p className="text-muted-foreground">
          Personaliza las restricciones y parámetros de práctica por grupo
        </p>
      </div>

      {/* Selección de Grupo */}
      <Card>
        <CardHeader>
          <CardTitle>Seleccionar Grupo</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="grupo">Grupo</Label>
            <select
              id="grupo"
              value={grupoId || ''}
              onChange={(e) => setGrupoId(e.target.value ? parseInt(e.target.value) : null)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">Selecciona un grupo...</option>
              {grupos?.map((grupo) => (
                <option key={grupo.id} value={grupo.id}>
                  {grupo.nombre} ({grupo.codigo_grupo})
                </option>
              ))}
            </select>
            {configuracionActual && (
              <div className="flex items-center gap-2 mt-2">
                <AlertCircle className="h-4 w-4 text-blue-500" />
                <span className="text-sm text-muted-foreground">
                  Este grupo tiene configuración activa desde:{' '}
                  {new Date(configuracionActual.fecha_aplicacion).toLocaleDateString('es-ES')}
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {grupoId && (
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Operaciones Permitidas */}
            <Card>
              <CardHeader>
                <CardTitle>Operaciones Permitidas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {operaciones.map((op) => (
                    <label
                      key={op.id}
                      className={`flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                        operacionesPermitidas.includes(op.id)
                          ? 'border-primary bg-primary/5'
                          : 'border-muted hover:border-muted-foreground/50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={operacionesPermitidas.includes(op.id)}
                        onChange={() => toggleOperacion(op.id)}
                        className="h-4 w-4"
                      />
                      <span className="font-medium">{op.nombre}</span>
                    </label>
                  ))}
                </div>
                {operacionesPermitidas.length === 0 && (
                  <p className="text-sm text-red-500 mt-2">
                    * Debes seleccionar al menos una operación
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Niveles Permitidos */}
            <Card>
              <CardHeader>
                <CardTitle>Niveles Permitidos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-3">
                  {niveles.map((nivel) => (
                    <label
                      key={nivel}
                      className={`flex items-center justify-center gap-2 p-4 rounded-lg border cursor-pointer transition-all flex-1 ${
                        nivelesPermitidos.includes(nivel)
                          ? 'border-primary bg-primary/5'
                          : 'border-muted hover:border-muted-foreground/50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={nivelesPermitidos.includes(nivel)}
                        onChange={() => toggleNivel(nivel)}
                        className="h-4 w-4"
                      />
                      <span className="font-medium">Nivel {nivel}</span>
                    </label>
                  ))}
                </div>
                {nivelesPermitidos.length === 0 && (
                  <p className="text-sm text-red-500 mt-2">
                    * Debes seleccionar al menos un nivel
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Rangos de Números */}
            <Card>
              <CardHeader>
                <CardTitle>Rangos de Números</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="rango_min">Rango Mínimo</Label>
                    <Input
                      id="rango_min"
                      type="number"
                      step="0.01"
                      value={rangoMin}
                      onChange={(e) => setRangoMin(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rango_max">Rango Máximo</Label>
                    <Input
                      id="rango_max"
                      type="number"
                      step="0.01"
                      value={rangoMax}
                      onChange={(e) => setRangoMax(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="decimales">Decimales Máximos</Label>
                    <Input
                      id="decimales"
                      type="number"
                      min="0"
                      max="5"
                      value={decimalesMaximos}
                      onChange={(e) => setDecimalesMaximos(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="bg-muted p-3 rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    <strong>Ejemplo:</strong> Con rango {rangoMin} a {rangoMax} y {decimalesMaximos}{' '}
                    decimales, se pueden generar números como: {parseFloat(rangoMin).toFixed(2)},{' '}
                    {(
                      (parseFloat(rangoMin) + parseFloat(rangoMax)) /
                      2
                    ).toFixed(parseInt(decimalesMaximos))}
                    , {parseFloat(rangoMax).toFixed(2)}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Pistas Habilitadas */}
            <Card>
              <CardHeader>
                <CardTitle>Pistas Habilitadas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {['nivel_1', 'nivel_2', 'nivel_3'].map((nivel) => (
                    <label
                      key={nivel}
                      className="flex items-center justify-between p-4 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <p className="font-medium">
                          Pista {nivel === 'nivel_1' ? 'Básica' : nivel === 'nivel_2' ? 'Media' : 'Avanzada'}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {nivel === 'nivel_1'
                            ? 'Ayuda básica sobre el concepto'
                            : nivel === 'nivel_2'
                            ? 'Orientación sobre el proceso'
                            : 'Ayuda detallada paso a paso'}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={pistasHabilitadas[nivel] || false}
                        onChange={() => togglePista(nivel)}
                        className="h-4 w-4"
                      />
                    </label>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Botones de Acción */}
            <div className="flex items-center gap-3 justify-end">
              {/* Feedback inline junto al botón */}
              {crearConfiguracionMutation.isSuccess && (
                <span className="text-sm text-green-600 font-medium flex items-center gap-1">
                  ✓ Configuración guardada exitosamente
                </span>
              )}
              {crearConfiguracionMutation.isError && (
                <span className="text-sm text-red-500 font-medium flex items-center gap-1">
                  ✗ Error al guardar. Intenta nuevamente.
                </span>
              )}
              <Button
                type="submit"
                disabled={
                  !grupoId ||
                  operacionesPermitidas.length === 0 ||
                  nivelesPermitidos.length === 0 ||
                  crearConfiguracionMutation.isPending
                }
              >
                <Save className="mr-2 h-4 w-4" />
                {crearConfiguracionMutation.isPending
                  ? 'Guardando...'
                  : configuracionActual
                  ? 'Actualizar Configuración'
                  : 'Guardar Configuración'}
              </Button>
            </div>
          </div>
        </form>
      )}

      {!grupoId && (
        <Card>
          <CardContent className="text-center py-12">
            <Settings className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Selecciona un Grupo</h3>
            <p className="text-muted-foreground">
              Elige un grupo para configurar los parámetros de práctica
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
