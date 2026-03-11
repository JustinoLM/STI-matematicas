/**
 * Página de monitoreo de alertas.
 * Muestra todas las alertas del sistema filtradas por severidad y estado.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, Filter, Eye, CheckCircle } from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function AlertsPage() {
  const [selectedTab, setSelectedTab] = useState<'all' | 'alta' | 'media' | 'baja'>('all');

  // Obtener alertas
  const { data: alertas, isLoading } = useQuery({
    queryKey: ['teacher', 'alerts'],
    queryFn: () => teacherService.getAlertas(),
  });

  // Filtrar alertas según tab seleccionado
  const filteredAlertas = alertas?.filter((alerta) => {
    if (selectedTab === 'all') return true;
    return alerta.severidad === selectedTab;
  });

  // Contar alertas por severidad (backend devuelve: 'alta', 'media', 'baja')
  const altaCount = alertas?.filter((a) => a.severidad === 'alta' && a.activa).length || 0;
  const mediaCount = alertas?.filter((a) => a.severidad === 'media' && a.activa).length || 0;
  const bajaCount = alertas?.filter((a) => a.severidad === 'baja' && a.activa).length || 0;
  const totalActive = alertas?.filter((a) => a.activa).length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Alertas y Monitoreo</h1>
        <p className="text-muted-foreground">
          Sistema de alertas para estudiantes que requieren atención
        </p>
      </div>

      {/* Estadísticas de Alertas */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Activas</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalActive}</div>
            <p className="text-xs text-muted-foreground">Requieren atención</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Prioridad Alta</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{altaCount}</div>
            <p className="text-xs text-muted-foreground">Rezagados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Prioridad Media</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{mediaCount}</div>
            <p className="text-xs text-muted-foreground">Inactivos / Estancados</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Prioridad Baja</CardTitle>
            <AlertTriangle className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{bajaCount}</div>
            <p className="text-xs text-muted-foreground">Excelencia</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs de Filtrado */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Alertas del Sistema</CardTitle>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Filter className="h-4 w-4" />
              Filtrar por severidad
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedTab} onValueChange={(v) => setSelectedTab(v as any)}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="all">
                Todas ({alertas?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="alta">
                Alta ({altaCount})
              </TabsTrigger>
              <TabsTrigger value="media">
                Media ({mediaCount})
              </TabsTrigger>
              <TabsTrigger value="baja">
                Baja ({bajaCount})
              </TabsTrigger>
            </TabsList>

            <TabsContent value={selectedTab} className="mt-6">
              {isLoading ? (
                <div className="text-center py-12 text-muted-foreground">
                  Cargando alertas...
                </div>
              ) : filteredAlertas && filteredAlertas.length > 0 ? (
                <div className="space-y-3">
                  {filteredAlertas.map((alerta) => (
                    <div
                      key={alerta.id}
                      className="flex items-start gap-3 rounded-lg border p-4 hover:bg-muted/50 transition-colors"
                    >
                      <AlertTriangle
                        className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                          alerta.severidad === 'alta'
                            ? 'text-red-500'
                            : alerta.severidad === 'media'
                            ? 'text-yellow-500'
                            : 'text-blue-500'
                        }`}
                      />

                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <h3 className="font-semibold">{alerta.titulo}</h3>
                              <Badge
                                variant={
                                  alerta.severidad === 'alta'
                                    ? 'destructive'
                                    : alerta.severidad === 'media'
                                    ? 'default'
                                    : 'secondary'
                                }
                              >
                                {alerta.severidad === 'alta' ? 'Alta' :
                                 alerta.severidad === 'media' ? 'Media' : 'Baja'}
                              </Badge>
                              {!alerta.activa && (
                                <Badge variant="outline">Resuelta</Badge>
                              )}
                              {alerta.leida && (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {alerta.mensaje}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-2 border-t">
                          <div className="flex flex-col gap-1">
                            <p className="text-sm font-medium">
                              {alerta.nombre_estudiante}
                            </p>
                            <code className="text-xs bg-muted px-2 py-1 rounded w-fit">
                              {alerta.codigo_estudiante}
                            </code>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {new Date(alerta.fecha_creacion).toLocaleDateString('es-ES', {
                                day: 'numeric',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            <Link to={`/teacher/students/${alerta.estudiante_id}`}>
                              <Button variant="outline" size="sm">
                                <Eye className="h-4 w-4 mr-2" />
                                Ver Estudiante
                              </Button>
                            </Link>
                          </div>
                        </div>

                        {/* Datos de contexto adicionales */}
                        {alerta.datos_contexto && Object.keys(alerta.datos_contexto).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                              Ver datos adicionales
                            </summary>
                            <div className="mt-2 p-2 bg-muted rounded text-xs">
                              <pre>{JSON.stringify(alerta.datos_contexto, null, 2)}</pre>
                            </div>
                          </details>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">
                    {selectedTab === 'all'
                      ? '¡No hay alertas!'
                      : `No hay alertas de tipo "${selectedTab}"`}
                  </h3>
                  <p className="text-muted-foreground">
                    Todo está funcionando correctamente
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Leyenda de Tipos de Alertas */}
      <Card>
        <CardHeader>
          <CardTitle>Tipos de Alertas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <span className="font-semibold text-red-600">Posible Trampa</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Patrones sospechosos de respuestas instantáneas
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <span className="font-semibold text-red-600">Rezagado</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Precisión menor al 50%
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <span className="font-semibold text-yellow-600">Inactivo</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Sin actividad en los últimos 7 días
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <span className="font-semibold text-yellow-600">Dificultad Persistente</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Estancado en el mismo nivel por mucho tiempo
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-500" />
                <span className="font-semibold text-blue-600">Promoción Rápida</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Avance muy rápido entre niveles
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-blue-500" />
                <span className="font-semibold text-blue-600">Excelencia</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Rendimiento sobresaliente (&gt;90%)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
