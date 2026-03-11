/**
 * Panel de estadísticas analíticas de grupo para el profesor.
 *
 * Acceso: /teacher/stats (selector de grupo integrado)
 * Muestra perfiles ML, alertas, niveles por operación,
 * actividad y análisis IA bajo demanda con exportación PDF.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
  Title,
} from 'chart.js';
import { Bar, Line, Doughnut, Radar } from 'react-chartjs-2';
import {
  Users,
  AlertTriangle,
  TrendingUp,
  Brain,
  Sparkles,
  FileDown,
  ChevronDown,
  ChevronUp,
  Shield,
  Clock,
  CheckCircle2,
  Star,
  Zap,
  BookOpen,
  Search,
  Filter,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { teacherService } from '@/services/teacherService';
import { statsService } from '@/services/statsService';
import type {
  GrupoStatsResponse,
  EstudianteStatsItem,
  Grupo,
} from '@/types';

// ── Registro de módulos de Chart.js ─────────────────────────────────────────
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
  Title
);

// ── Paleta de colores consistente ───────────────────────────────────────────
const COLORS = {
  rapido_preciso: '#22c55e',
  cuidadoso_metodico: '#3b82f6',
  impulsivo: '#f59e0b',
  en_desarrollo: '#ef4444',
  no_clasificado: '#94a3b8',
  suma: '#6366f1',
  resta: '#ec4899',
  multiplicacion: '#f97316',
  division: '#14b8a6',
};

const PERFIL_LABELS: Record<string, string> = {
  rapido_preciso: 'Rápido y Preciso',
  cuidadoso_metodico: 'Cuidadoso y Metódico',
  impulsivo: 'Impulsivo',
  en_desarrollo: 'En Desarrollo',
  no_clasificado: 'Sin Clasificar',
};

const ALERTA_META: Record<
  string,
  { label: string; color: string; icon: React.ComponentType<{ className?: string }> }
> = {
  posible_trampa: { label: 'Posible trampa', color: 'bg-red-100 text-red-700 border-red-300', icon: Shield },
  rezagado: { label: 'Rezagados', color: 'bg-orange-100 text-orange-700 border-orange-300', icon: TrendingUp },
  inactivo: { label: 'Inactivos', color: 'bg-gray-100 text-gray-700 border-gray-300', icon: Clock },
  promocion_rapida: { label: 'Promoción rápida', color: 'bg-purple-100 text-purple-700 border-purple-300', icon: Zap },
  dificultad_persistente: { label: 'Dificultad persistente', color: 'bg-yellow-100 text-yellow-700 border-yellow-300', icon: BookOpen },
  excelencia: { label: 'Excelencia', color: 'bg-green-100 text-green-700 border-green-300', icon: Star },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatFecha(fecha: string): string {
  const d = new Date(fecha + 'T00:00:00');
  return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short' });
}

function colorProbabilidad(prob: number): string {
  if (prob >= 70) return 'text-green-600';
  if (prob >= 40) return 'text-yellow-600';
  return 'text-red-500';
}

function badgePerfil(perfil: string) {
  const label = PERFIL_LABELS[perfil] ?? perfil;
  const color = (COLORS as Record<string, string>)[perfil] ?? '#94a3b8';
  return (
    <span
      className="inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  );
}

// ── Componente: Fila expandible de estudiante ────────────────────────────────

function EstudianteRow({ est }: { est: EstudianteStatsItem }) {
  const [expanded, setExpanded] = useState(false);

  const radarData = {
    labels: ['Suma', 'Resta', 'Multiplicación', 'División'],
    datasets: [
      {
        label: est.nombre,
        data: [est.nivel_suma, est.nivel_resta, est.nivel_multiplicacion, est.nivel_division],
        backgroundColor: 'rgba(99,102,241,0.15)',
        borderColor: '#6366f1',
        borderWidth: 2,
        pointBackgroundColor: '#6366f1',
      },
    ],
  };

  const radarOptions = {
    scales: {
      r: {
        min: 0,
        max: 5,
        ticks: { stepSize: 1, font: { size: 10 } },
        pointLabels: { font: { size: 11 } },
      },
    },
    plugins: { legend: { display: false } },
  };

  const actividadData = {
    labels: est.actividad_14_dias.map((d) => formatFecha(d.fecha)),
    datasets: [
      {
        data: est.actividad_14_dias.map((d) => d.sesiones),
        backgroundColor: 'rgba(99,102,241,0.6)',
        borderRadius: 4,
      },
    ],
  };

  const actividadOptions = {
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { font: { size: 9 } } },
      y: { ticks: { stepSize: 1, font: { size: 9 } }, min: 0 },
    },
  };

  const tieneAlertas = est.alertas.length > 0;

  return (
    <>
      <tr
        className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            )}
            <div>
              <p className="text-sm font-medium">{est.nombre}</p>
              <p className="text-xs text-muted-foreground">{est.codigo}</p>
            </div>
          </div>
        </td>
        <td className="px-3 py-2.5 text-center">
          <span className="text-sm font-semibold">{est.nivel_actual}</span>
          <span className="text-xs text-muted-foreground">/5</span>
        </td>
        <td className="px-3 py-2.5">{badgePerfil(est.perfil_aprendizaje)}</td>
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            <Progress value={est.precision} className="h-1.5 w-16" />
            <span className="text-xs text-muted-foreground w-10">{est.precision.toFixed(0)}%</span>
          </div>
        </td>
        <td className="px-3 py-2.5 text-center text-sm">{est.sesiones_esta_semana}</td>
        <td className="px-3 py-2.5 text-center">
          <span
            className={`text-sm ${est.dias_sin_practicar >= 7 ? 'text-red-500 font-medium' : 'text-muted-foreground'}`}
          >
            {est.dias_sin_practicar}d
          </span>
        </td>
        <td className="px-3 py-2.5 text-center">
          <span className={`text-sm font-semibold ${colorProbabilidad(est.probabilidad_avance)}`}>
            {est.probabilidad_avance.toFixed(0)}%
          </span>
        </td>
        <td className="px-3 py-2.5">
          {tieneAlertas ? (
            <div className="flex flex-wrap gap-1">
              {est.alertas.slice(0, 2).map((a) => {
                const meta = ALERTA_META[a];
                return meta ? (
                  <span
                    key={a}
                    className={`text-xs px-1.5 py-0.5 rounded border font-medium ${meta.color}`}
                  >
                    {meta.label}
                  </span>
                ) : null;
              })}
              {est.alertas.length > 2 && (
                <span className="text-xs text-muted-foreground">+{est.alertas.length - 2}</span>
              )}
            </div>
          ) : (
            <CheckCircle2 className="h-4 w-4 text-green-400" />
          )}
        </td>
      </tr>

      {expanded && (
        <tr className="bg-muted/10">
          <td colSpan={8} className="px-6 py-4">
            <div className="grid grid-cols-2 gap-6 max-w-2xl">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                  Niveles por operación
                </p>
                <div className="h-44">
                  <Radar data={radarData} options={radarOptions} />
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                  Actividad (últimas 2 semanas)
                </p>
                <div className="h-44">
                  <Bar data={actividadData} options={actividadOptions} />
                </div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-muted-foreground">
              <span>Total sesiones: <strong className="text-foreground">{est.total_sesiones}</strong></span>
              <span>Velocidad promedio: <strong className="text-foreground">{est.velocidad_promedio.toFixed(1)} seg/prob</strong></span>
              <span>Confianza perfil ML: <strong className="text-foreground">{est.confianza_perfil.toFixed(0)}%</strong></span>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Componente principal ─────────────────────────────────────────────────────

export default function GroupStatsPage() {
  const [grupoSeleccionado, setGrupoSeleccionado] = useState<number | null>(null);
  const [analisisTexto, setAnalisisTexto] = useState<string | null>(null);
  const [exportModal, setExportModal] = useState(false);
  const [exportSections, setExportSections] = useState({
    tabla: true,
    perfiles: true,
    niveles: true,
    actividad: true,
    precision: true,
    alertas: true,
    analisis: false,
  });

  // ── Filtros de la tabla de estudiantes ───────────────────────────────────
  const [filtroBusqueda, setFiltroBusqueda] = useState('');
  const [filtroNivel, setFiltroNivel] = useState<number | null>(null);
  const [filtroPerfil, setFiltroPerfil] = useState<string | null>(null);
  const [filtroAlerta, setFiltroAlerta] = useState<'todos' | 'con' | 'sin'>('todos');

  /** Resetea todos los filtros y vuelve al selector de grupo */
  const handleCambiarGrupo = () => {
    setGrupoSeleccionado(null);
    setFiltroBusqueda('');
    setFiltroNivel(null);
    setFiltroPerfil(null);
    setFiltroAlerta('todos');
  };

  // Grupos del profesor
  const { data: grupos } = useQuery<Grupo[]>({
    queryKey: ['teacher', 'groups'],
    queryFn: () => teacherService.getGrupos(),
  });

  // Estadísticas del grupo seleccionado
  const { data: stats, isLoading: loadingStats } = useQuery<GrupoStatsResponse>({
    queryKey: ['stats', 'grupo', grupoSeleccionado],
    queryFn: () => statsService.getGrupoStats(grupoSeleccionado!),
    enabled: !!grupoSeleccionado,
    staleTime: 2 * 60 * 1000, // 2 minutos
  });

  // Análisis IA (bajo demanda)
  const analizarMutation = useMutation({
    mutationFn: () => statsService.analizarConIA(grupoSeleccionado!),
    onSuccess: (data) => setAnalisisTexto(data.texto),
  });

  // ── Exportar PDF (html2canvas no instalado — usamos window.print) ──────────
  const handleExport = async () => {
    if (!stats) return;
    setExportModal(false);
    // Generamos análisis si fue seleccionado y aún no existe
    if (exportSections.analisis && !analisisTexto) {
      const res = await statsService.analizarConIA(grupoSeleccionado!);
      setAnalisisTexto(res.texto);
    }
    setTimeout(() => window.print(), 300);
  };

  // ── Sin grupo seleccionado: selector ────────────────────────────────────────
  if (!grupoSeleccionado) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6 text-indigo-500" />
            Estadísticas de Grupo
          </h1>
          <p className="text-muted-foreground mt-1">
            Selecciona un grupo para ver el análisis detallado con perfiles ML y métricas.
          </p>
        </div>

        {!grupos ? (
          <p className="text-muted-foreground">Cargando grupos...</p>
        ) : grupos.length === 0 ? (
          <p className="text-muted-foreground">No tienes grupos creados aún.</p>
        ) : (
          <div className="grid gap-3">
            {grupos.map((g) => (
              <Card
                key={g.id}
                className="cursor-pointer hover:shadow-md transition-shadow border hover:border-indigo-300"
                onClick={() => setGrupoSeleccionado(g.id)}
              >
                <CardContent className="flex items-center justify-between py-4 px-5">
                  <div className="flex items-center gap-3">
                    <Users className="h-5 w-5 text-indigo-400" />
                    <div>
                      <p className="font-semibold">{g.nombre}</p>
                      <p className="text-xs text-muted-foreground">{g.codigo_grupo}</p>
                    </div>
                  </div>
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Cargando estadísticas ────────────────────────────────────────────────────
  if (loadingStats || !stats) {
    return (
      <div className="p-6">
        <button
          className="text-sm text-muted-foreground hover:underline mb-4 flex items-center gap-1"
          onClick={handleCambiarGrupo}
        >
          ← Cambiar grupo
        </button>
        <div className="flex items-center gap-2 text-muted-foreground mt-8 justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          Cargando estadísticas...
        </div>
      </div>
    );
  }

  // ── Filtrado de estudiantes ──────────────────────────────────────────────────
  const estudiantesFiltrados = stats.estudiantes.filter(est => {
    if (filtroBusqueda && !est.nombre.toLowerCase().includes(filtroBusqueda.toLowerCase())) return false;
    if (filtroNivel !== null && est.nivel_actual !== filtroNivel) return false;
    if (filtroPerfil && est.perfil_aprendizaje !== filtroPerfil) return false;
    if (filtroAlerta === 'con' && est.alertas.length === 0) return false;
    if (filtroAlerta === 'sin' && est.alertas.length > 0) return false;
    return true;
  });
  const hayFiltrosActivos =
    filtroBusqueda !== '' || filtroNivel !== null || filtroPerfil !== null || filtroAlerta !== 'todos';
  const limpiarFiltros = () => {
    setFiltroBusqueda('');
    setFiltroNivel(null);
    setFiltroPerfil(null);
    setFiltroAlerta('todos');
  };

  // ── Datos para gráficos ──────────────────────────────────────────────────────
  const dist = stats.distribucion_perfiles;
  const doughnutData = {
    labels: Object.values(PERFIL_LABELS),
    datasets: [
      {
        data: [
          dist.rapido_preciso,
          dist.cuidadoso_metodico,
          dist.impulsivo,
          dist.en_desarrollo,
          dist.no_clasificado,
        ],
        backgroundColor: Object.values(COLORS).slice(0, 5),
        borderWidth: 1,
        borderColor: '#fff',
      },
    ],
  };

  const niv = stats.niveles_por_operacion;
  const barNivelesData = {
    labels: ['Nivel 1', 'Nivel 2', 'Nivel 3', 'Nivel 4', 'Nivel 5'],
    datasets: [
      { label: 'Suma', data: niv.suma, backgroundColor: COLORS.suma },
      { label: 'Resta', data: niv.resta, backgroundColor: COLORS.resta },
      { label: 'Multiplicación', data: niv.multiplicacion, backgroundColor: COLORS.multiplicacion },
      { label: 'División', data: niv.division, backgroundColor: COLORS.division },
    ],
  };

  const actividadData = {
    labels: stats.actividad_grupal.map((d) => formatFecha(d.fecha)),
    datasets: [
      {
        label: 'Sesiones',
        data: stats.actividad_grupal.map((d) => d.sesiones),
        fill: true,
        backgroundColor: 'rgba(99,102,241,0.12)',
        borderColor: '#6366f1',
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 3,
      },
    ],
  };

  const precisionData = {
    labels: stats.precision_semanal.map((d) => d.semana),
    datasets: [
      {
        label: 'Precisión (%)',
        data: stats.precision_semanal.map((d) => d.precision),
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34,197,94,0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 4,
        pointBackgroundColor: '#22c55e',
      },
    ],
  };

  const precisionOptions = {
    scales: { y: { min: 0, max: 100, ticks: { callback: (v: number | string) => `${v}%` } } },
    plugins: { legend: { display: false } },
  };

  const alertasTotales = Object.values(stats.resumen_alertas).reduce((a, b) => a + b, 0);
  const avgPrecision =
    stats.estudiantes.length > 0
      ? stats.estudiantes.reduce((a, e) => a + e.precision, 0) / stats.estudiantes.length
      : 0;
  const avgNivel =
    stats.estudiantes.length > 0
      ? stats.estudiantes.reduce((a, e) => a + e.nivel_actual, 0) / stats.estudiantes.length
      : 0;

  return (
    <div className="p-4 space-y-5 max-w-7xl mx-auto print:p-2">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <button
            className="text-xs text-muted-foreground hover:underline mb-1 flex items-center gap-1"
            onClick={handleCambiarGrupo}
          >
            ← Cambiar grupo
          </button>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Brain className="h-5 w-5 text-indigo-500" />
            {stats.grupo_nombre}
            <Badge variant="secondary">{stats.total_estudiantes} estudiantes</Badge>
          </h1>
        </div>
        <div className="flex gap-2 print:hidden">
          <Button
            variant="outline"
            size="sm"
            onClick={() => analizarMutation.mutate()}
            disabled={analizarMutation.isPending || !grupoSeleccionado}
          >
            {analizarMutation.isPending ? (
              <>
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent mr-1.5" />
                Analizando...
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 mr-1.5 text-indigo-500" />
                Analizar con IA
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExportModal(true)}
          >
            <FileDown className="h-3.5 w-3.5 mr-1.5" />
            Exportar PDF
          </Button>
        </div>
      </div>

      {/* Cards de resumen */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground">Precisión promedio</p>
            <p className="text-2xl font-bold text-green-600">{avgPrecision.toFixed(1)}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground">Nivel promedio</p>
            <p className="text-2xl font-bold">{avgNivel.toFixed(1)}<span className="text-sm text-muted-foreground">/5</span></p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground">Alertas activas</p>
            <p className={`text-2xl font-bold ${alertasTotales > 0 ? 'text-amber-500' : 'text-green-500'}`}>
              {alertasTotales}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground">Perfiles clasificados</p>
            <p className="text-2xl font-bold">
              {stats.total_estudiantes - dist.no_clasificado}
              <span className="text-sm text-muted-foreground">/{stats.total_estudiantes}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alertas activas (si existen) */}
      {alertasTotales > 0 && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Alertas activas
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.resumen_alertas).map(([key, count]) => {
                if (count === 0) return null;
                const meta = ALERTA_META[key];
                if (!meta) return null;
                const Icon = meta.icon;
                return (
                  <div
                    key={key}
                    className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium ${meta.color}`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {meta.label}: <strong>{count}</strong>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gráficos fila 1: Perfiles ML + Niveles por operación */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm">Distribución de perfiles ML</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 flex justify-center">
            <div className="h-56 w-56">
              <Doughnut
                data={doughnutData}
                options={{
                  plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 8 } },
                  },
                  cutout: '55%',
                }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm">Niveles por operación</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="h-56">
              <Bar
                data={barNivelesData}
                options={{
                  plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 8 } } },
                  scales: { y: { ticks: { stepSize: 1 }, min: 0 } },
                }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos fila 2: Actividad + Precisión semanal */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm">Actividad del grupo (últimas 2 semanas)</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="h-44">
              <Line
                data={actividadData}
                options={{
                  plugins: { legend: { display: false } },
                  scales: { y: { min: 0, ticks: { stepSize: 1 } } },
                }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm">Precisión semanal del grupo</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="h-44">
              {stats.precision_semanal.length > 0 ? (
                <Line data={precisionData} options={precisionOptions} />
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  Sin datos de las últimas 4 semanas
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabla de estudiantes */}
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <Users className="h-4 w-4" />
            Estudiantes — haz clic en una fila para ver el detalle
          </CardTitle>
        </CardHeader>

        {/* ── Filtros ─────────────────────────────────────────────────────── */}
        <div className="px-4 pb-3 space-y-2 print:hidden">

          {/* Búsqueda por nombre */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Buscar por nombre..."
              value={filtroBusqueda}
              onChange={e => setFiltroBusqueda(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Filtro por nivel */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-muted-foreground font-medium flex items-center gap-1 shrink-0">
              <Filter className="h-3 w-3" /> Nivel:
            </span>
            {([null, 1, 2, 3, 4, 5] as (number | null)[]).map(n => (
              <button
                key={n ?? 'todos'}
                onClick={() => setFiltroNivel(n)}
                className={`px-2.5 py-0.5 rounded-full border transition-colors ${
                  filtroNivel === n
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-border hover:bg-muted'
                }`}
              >
                {n === null ? 'Todos' : `N${n}`}
              </button>
            ))}

            <span className="text-muted-foreground/30 px-1">|</span>

            {/* Filtro por alertas */}
            <span className="text-muted-foreground font-medium shrink-0">Alertas:</span>
            {([
              { key: 'todos' as const, label: 'Todos' },
              { key: 'con'   as const, label: 'Con alertas' },
              { key: 'sin'   as const, label: 'Sin alertas' },
            ]).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFiltroAlerta(key)}
                className={`px-2.5 py-0.5 rounded-full border transition-colors ${
                  filtroAlerta === key
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-border hover:bg-muted'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Filtro por perfil ML */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-muted-foreground font-medium shrink-0">Perfil:</span>
            <button
              onClick={() => setFiltroPerfil(null)}
              className={`px-2.5 py-0.5 rounded-full border transition-colors ${
                filtroPerfil === null
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background border-border hover:bg-muted'
              }`}
            >
              Todos
            </button>
            {Object.entries(PERFIL_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setFiltroPerfil(filtroPerfil === key ? null : key)}
                className="px-2.5 py-0.5 rounded-full border transition-colors"
                style={
                  filtroPerfil === key
                    ? { backgroundColor: (COLORS as Record<string, string>)[key], color: '#fff', borderColor: 'transparent' }
                    : {}
                }
              >
                {label}
              </button>
            ))}
          </div>

          {/* Contador + limpiar filtros */}
          {hayFiltrosActivos && (
            <div className="flex items-center justify-between pt-0.5">
              <p className="text-xs text-muted-foreground">
                Mostrando <strong>{estudiantesFiltrados.length}</strong> de {stats.estudiantes.length} estudiantes
              </p>
              <button
                onClick={limpiarFiltros}
                className="text-xs text-primary hover:underline"
              >
                Limpiar filtros
              </button>
            </div>
          )}
        </div>

        <CardContent className="px-0 pb-0 overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b bg-muted/40 text-xs text-muted-foreground uppercase tracking-wide">
                <th className="px-3 py-2">Estudiante</th>
                <th className="px-3 py-2 text-center">Nivel</th>
                <th className="px-3 py-2">Perfil ML</th>
                <th className="px-3 py-2">Precisión</th>
                <th className="px-3 py-2 text-center">Ses./semana</th>
                <th className="px-3 py-2 text-center">Inactivo</th>
                <th className="px-3 py-2 text-center">Prob. avance</th>
                <th className="px-3 py-2">Alertas</th>
              </tr>
            </thead>
            <tbody>
              {estudiantesFiltrados.length > 0 ? (
                estudiantesFiltrados.map((est) => (
                  <EstudianteRow key={est.id} est={est} />
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No hay estudiantes que coincidan con los filtros seleccionados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Panel de análisis IA */}
      {analisisTexto && (
        <Card className="border-indigo-200 bg-indigo-50/30">
          <CardHeader className="pb-2 pt-4 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-500" />
              Análisis pedagógico — DeepSeek
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{analisisTexto}</p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-3 h-7 text-xs text-muted-foreground"
              onClick={() => analizarMutation.mutate()}
              disabled={analizarMutation.isPending}
            >
              Regenerar análisis
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Modal de exportación */}
      {exportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 print:hidden">
          <div className="bg-background rounded-lg shadow-xl p-6 w-full max-w-sm mx-4">
            <h2 className="font-semibold text-base mb-4 flex items-center gap-2">
              <FileDown className="h-4 w-4" />
              Exportar informe PDF
            </h2>
            <p className="text-xs text-muted-foreground mb-3">
              Selecciona las secciones a incluir:
            </p>
            <div className="space-y-2">
              {(
                [
                  ['tabla', 'Tabla de estudiantes'],
                  ['perfiles', 'Distribución de perfiles ML'],
                  ['niveles', 'Niveles por operación'],
                  ['actividad', 'Actividad del grupo'],
                  ['precision', 'Precisión semanal'],
                  ['alertas', 'Panel de alertas'],
                  ['analisis', 'Análisis IA (genera bajo demanda)'],
                ] as [keyof typeof exportSections, string][]
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={exportSections[key]}
                    onChange={(e) =>
                      setExportSections((prev) => ({ ...prev, [key]: e.target.checked }))
                    }
                    className="rounded"
                  />
                  <span className="text-sm">{label}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-2 mt-5">
              <Button className="flex-1" onClick={handleExport}>
                Exportar
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setExportModal(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Estilos de impresión */}
      <style>{`
        @media print {
          .print\\:hidden { display: none !important; }
          .print\\:p-2 { padding: 0.5rem; }
          body { font-size: 12px; }
        }
      `}</style>
    </div>
  );
}
