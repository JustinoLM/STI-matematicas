/**
 * Página de detalle de un estudiante específico (vista del profesor).
 * Muestra exactamente la misma pantalla de progreso que ve el estudiante.
 */

import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  TrendingUp,
  Target,
  Clock,
  Loader2,
  Lock,
} from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { diaLocalHace, formatearFecha } from '@/lib/fechas';

const OP_CONFIG: Record<string, { label: string; colorBar: string }> = {
  suma:           { label: 'Suma',           colorBar: 'bg-blue-500' },
  resta:          { label: 'Resta',          colorBar: 'bg-green-500' },
  multiplicacion: { label: 'Multiplicación', colorBar: 'bg-purple-500' },
  division:       { label: 'División',       colorBar: 'bg-orange-500' },
};

function formatSegundos(segundos: number): string {
  if (!segundos) return '0 min';
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m} min`;
}

export default function StudentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const estudianteId = parseInt(id || '0');

  const { data: perfil, isLoading: loadingPerfil } = useQuery({
    queryKey: ['teacher', 'student', estudianteId, 'profile'],
    queryFn: () => teacherService.getPerfilEstudiante(estudianteId),
    enabled: !!estudianteId,
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['teacher', 'student', estudianteId, 'stats'],
    queryFn: () => teacherService.getStatsEstudiante(estudianteId),
    enabled: !!estudianteId,
  });

  const isLoading = loadingPerfil || loadingStats;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <p className="text-muted-foreground">Cargando progreso del estudiante...</p>
      </div>
    );
  }

  if (!perfil) {
    return (
      <div className="space-y-6">
        <Link to="/teacher/students">
          <Button variant="ghost">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Estudiantes
          </Button>
        </Link>
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-muted-foreground">Estudiante no encontrado</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Datos derivados (misma lógica que ProgressPage) ──────────────────────

  const nivelActual = perfil?.nivel_actual ?? 1;
  const umbral = perfil?.umbral_promocion ?? 10;
  const consecutivas = perfil?.consecutivas_por_operacion ?? {};
  const opDisponibles: string[] = perfil?.operaciones_disponibles ?? [];
  const progresoNivel =
    opDisponibles.length > 0
      ? Math.round(
          (opDisponibles.reduce((acc: number, op: string) => acc + Math.min((consecutivas[op] ?? 0), umbral), 0) /
            (opDisponibles.length * umbral)) *
            100
        )
      : 0;

  const operacionesBE: any[] = stats?.stats_por_operacion ?? [];
  const opOrden = ['suma', 'resta', 'multiplicacion', 'division'];

  const tiempoEstimadoSeg =
    stats && stats.total_problemas_resueltos > 0 && stats.velocidad_promedio_global > 0
      ? Math.round(stats.total_problemas_resueltos * stats.velocidad_promedio_global)
      : 0;

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <div className="space-y-1">
        <Link to="/teacher/students">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Estudiantes
          </Button>
        </Link>
        {perfil?.nombre_estudiante && (
          <h1 className="text-2xl font-bold">{perfil.nombre_estudiante}</h1>
        )}
      </div>

      {/* Header — igual que ProgressPage */}
      <Card className="bg-gradient-to-r from-green-50 to-emerald-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <TrendingUp className="h-8 w-8 text-green-600" />
            <div>
              <h2 className="text-2xl font-bold">Progreso del Estudiante</h2>
              <p className="text-sm text-gray-600 font-normal">Nivel {nivelActual} de 5</p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progreso al siguiente nivel</span>
              <span className="font-bold">{progresoNivel}%</span>
            </div>
            <Progress value={progresoNivel} className="h-3" />
          </div>
        </CardContent>
      </Card>

      {/* Estadísticas generales */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-2">
              <Target className="h-8 w-8 mx-auto text-blue-500" />
              <p className="text-2xl font-bold">{stats?.total_problemas_resueltos ?? 0}</p>
              <p className="text-sm text-gray-600">Problemas resueltos</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-2">
              <Clock className="h-8 w-8 mx-auto text-purple-500" />
              <p className="text-2xl font-bold">{formatSegundos(tiempoEstimadoSeg)}</p>
              <p className="text-sm text-gray-600">Tiempo estimado</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progreso por operación */}
      <Card>
        <CardHeader>
          <CardTitle>Progreso por Operación</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {opOrden.map((opKey) => {
              const cfg = OP_CONFIG[opKey];
              const opStats = operacionesBE.find((o) => o.operacion === opKey);
              const disponible = opDisponibles.includes(opKey);
              const nivelOp = opStats?.nivel_actual ?? 1;
              const consec = consecutivas[opKey] ?? 0;
              const progresoOp = Math.min(Math.round((consec / umbral) * 100), 100);
              const precision = opStats ? Math.round(opStats.precision * 100) : 0;
              const problemas = opStats?.problemas_resueltos ?? 0;

              return (
                <div key={opKey} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${cfg.colorBar}`} />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{cfg.label}</p>
                          {!disponible && (
                            <Lock className="h-3 w-3 text-gray-400" aria-label="Bloqueada" />
                          )}
                        </div>
                        <p className="text-sm text-gray-600">
                          Nivel {nivelOp} • {problemas} problemas • {precision}% precisión
                        </p>
                      </div>
                    </div>
                    <span className="text-sm font-bold">{progresoOp}%</span>
                  </div>
                  <Progress
                    value={disponible ? progresoOp : 0}
                    className={`h-2 ${!disponible ? 'opacity-30' : ''}`}
                  />
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Precisión global */}
      <Card>
        <CardHeader>
          <CardTitle>Precisión Global</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex-1 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Precisión en los últimos 15 intentos</span>
                <span className="font-bold">
                  {perfil ? Math.round(Number(perfil.precision_ultimos_15) * 100) : 0}%
                </span>
              </div>
              <Progress
                value={perfil ? Math.round(Number(perfil.precision_ultimos_15) * 100) : 0}
                className="h-3"
              />
            </div>
            <div className="text-center min-w-[80px]">
              <p className="text-3xl font-bold text-green-600">
                {stats ? Math.round(stats.precision_global * 100) : 0}%
              </p>
              <p className="text-xs text-gray-500">Precisión global</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sesiones de los últimos 7 días */}
      {stats && stats.sesiones_ultimos_7_dias?.some((s: number) => s > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>Últimos 7 Días</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-24">
              {(stats.sesiones_ultimos_7_dias as number[]).map((sesiones, i) => {
                const maxSesiones = Math.max(...stats.sesiones_ultimos_7_dias, 1);
                const altura = Math.round((sesiones / maxSesiones) * 100);
                const diasAtras = 6 - i;
                const diaSemana = formatearFecha(diaLocalHace(diasAtras), { weekday: 'short' }, 'es-ES');

                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs text-gray-500">{sesiones > 0 ? sesiones : ''}</span>
                    <div className="w-full flex items-end justify-center" style={{ height: '72px' }}>
                      <div
                        className="w-full bg-green-400 rounded-t transition-all"
                        style={{ height: `${altura}%`, minHeight: sesiones > 0 ? '4px' : '0' }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 capitalize">{diaSemana}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
