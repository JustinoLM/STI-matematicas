/**
 * Página de Progreso — datos reales del backend.
 * GET /adaptive/profile  → niveles, precisión, consecutivas
 * GET /practices/stats   → totales, rachas, tiempo
 */

import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, Target, Clock, Loader2, Lock, RefreshCw } from 'lucide-react';
import { studentService } from '@/services/studentService';
import apiClient from '@/services/api';

// ─── Tipos de stats ───────────────────────────────────────────────────────────

interface StatsPerOperation {
  operacion: string;
  nivel_actual: number;
  total_intentos: number;
  total_correctos: number;
  precision: number;
  velocidad_promedio: number;
  problemas_resueltos: number;
}

interface GlobalStats {
  estudiante_id: number;
  total_sesiones: number;
  total_sesiones_completas: number;
  total_problemas_resueltos: number;
  total_problemas_correctos: number;
  precision_global: number;
  velocidad_promedio_global: number;
  racha_actual_perfectas: number;
  mejor_racha_perfectas: number;
  dias_consecutivos_practicando: number;
  stats_por_operacion: StatsPerOperation[];
  precision_ultimos_7_dias: number[];
  sesiones_ultimos_7_dias: number[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const OP_CONFIG: Record<string, { label: string; color: string; colorBar: string }> = {
  suma:           { label: 'Suma',           color: 'text-blue-600',   colorBar: 'bg-blue-500' },
  resta:          { label: 'Resta',          color: 'text-green-600',  colorBar: 'bg-green-500' },
  multiplicacion: { label: 'Multiplicación', color: 'text-purple-600', colorBar: 'bg-purple-500' },
  division:       { label: 'División',       color: 'text-orange-600', colorBar: 'bg-orange-500' },
};

function formatSegundos(segundos: number): string {
  if (!segundos) return '0 min';
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m} min`;
}

// ─── Componente ───────────────────────────────────────────────────────────────

export function ProgressPage() {
  const navigate = useNavigate();

  // Mensaje motivacional LLM — React Query lo cachea 24h en el cliente
  const { data: mensajeLLM } = useQuery({
    queryKey: ['mensaje-progreso'],
    queryFn: () => studentService.getMensajeMotivacional('progreso'),
    staleTime: 1000 * 60 * 60 * 24,
    retry: false,
  });

  const { data: perfil, isLoading: loadingPerfil } = useQuery({
    queryKey: ['perfil-estudiante'],
    queryFn: () => studentService.getPerfil(),
    staleTime: 1000 * 60 * 5,
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['stats-globales'],
    queryFn: async (): Promise<GlobalStats> => {
      const response = await apiClient.get<GlobalStats>('/practices/stats');
      return response.data;
    },
    staleTime: 1000 * 60 * 5,
  });

  const { data: redencion } = useQuery({
    queryKey: ['redencion-disponible'],
    queryFn: () => studentService.getRedenciónDisponible(),
    staleTime: 1000 * 60 * 2,
    retry: false,
  });

  const isLoading = loadingPerfil || loadingStats;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-green-500" />
      </div>
    );
  }

  // ── Datos derivados ────────────────────────────────────────────────────────

  const nivelActual = perfil?.nivel_actual ?? 1;
  const umbral = perfil?.umbral_promocion ?? 10;
  const consecutivas = perfil?.consecutivas_por_operacion ?? {};

  // Progreso al siguiente nivel: promedio de consecutivas de todas las operaciones / umbral
  const opDisponibles = perfil?.operaciones_disponibles ?? [];
  const progresoNivel =
    opDisponibles.length > 0
      ? Math.round(
          (opDisponibles.reduce((acc: number, op: string) => acc + Math.min((consecutivas[op] ?? 0), umbral), 0) /
            (opDisponibles.length * umbral)) *
            100
        )
      : 0;

  // Operaciones del backend
  const operacionesBE = stats?.stats_por_operacion ?? [];
  const opOrden = ['suma', 'resta', 'multiplicacion', 'division'];

  // Tiempo total aproximado (velocidad_promedio * total_problemas ≈ segundos)
  const tiempoEstimadoSeg =
    stats && stats.total_problemas_resueltos > 0 && stats.velocidad_promedio_global > 0
      ? Math.round(stats.total_problemas_resueltos * stats.velocidad_promedio_global)
      : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gradient-to-r from-green-50 to-emerald-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <TrendingUp className="h-8 w-8 text-green-600" />
            <div>
              <h1 className="text-2xl font-bold">Mi Progreso</h1>
              <p className="text-sm text-gray-600 font-normal">
                Nivel {nivelActual} de 5
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Mensaje motivacional (genérico hasta que llega el LLM) */}
          <p className="text-gray-700 italic text-sm">
            {mensajeLLM ?? '¡Mira cuánto has aprendido! Cada problema resuelto te hace más fuerte.'}
          </p>
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
              <p className="text-2xl font-bold">
                {stats?.total_problemas_resueltos ?? 0}
              </p>
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

      {/* Redención */}
      {redencion?.disponible && (
        <Card className="border-2 border-orange-300 bg-gradient-to-r from-orange-50 to-amber-50">
          <CardContent className="pt-5">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-full">
                  <RefreshCw className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                  <p className="font-semibold text-orange-800">Redención disponible</p>
                  <p className="text-sm text-orange-600">
                    {redencion.total_problemas_fallados} problema{redencion.total_problemas_fallados !== 1 ? 's' : ''} pendiente{redencion.total_problemas_fallados !== 1 ? 's' : ''} — practica 5 y demuestra que aprendiste
                  </p>
                </div>
              </div>
              <Button
                onClick={() => navigate('/student/practice?mode=redencion')}
                className="bg-orange-500 hover:bg-orange-600 text-white shrink-0"
              >
                Redención
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

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
                    value={progresoOp}
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
      {stats && stats.sesiones_ultimos_7_dias.some((s) => s > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>Últimos 7 Días</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 h-24">
              {stats.sesiones_ultimos_7_dias.map((sesiones, i) => {
                const maxSesiones = Math.max(...stats.sesiones_ultimos_7_dias, 1);
                const altura = Math.round((sesiones / maxSesiones) * 100);
                const diasAtras = 6 - i;
                const fecha = new Date();
                fecha.setDate(fecha.getDate() - diasAtras);
                const diaSemana = fecha.toLocaleDateString('es-ES', { weekday: 'short' });

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
