/**
 * Página de desafíos grupales del estudiante.
 * Muestra los retos asignados al grupo por el profesor, con progreso en tiempo real.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Target,
  Users,
  Clock,
  Trophy,
  BookOpen,
  Zap,
  CheckCircle2,
  AlertCircle,
  Gift,
  Loader2,
  CheckSquare,
  Shield,
  Timer,
  Coins,
  Medal,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { studentService } from '@/services/studentService';
import type { DesafioEstudiante } from '@/types';

// ─── Helpers ─────────────────────────────────────────────────────────────────

type TipoDesafio = DesafioEstudiante['tipo'];

interface TipoInfo {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  dificultad: number;
  dificultadLabel: string;
  dificultadColor: string;
  descripcionMeta: (obj: number, param?: number) => string;
}

const TIPO_META: Record<TipoDesafio, TipoInfo> = {
  problemas_resueltos: {
    label: 'Resolver problemas',
    icon: BookOpen,
    dificultad: 1,
    dificultadLabel: 'Fácil',
    dificultadColor: 'bg-green-100 text-green-700 border-green-300',
    descripcionMeta: (obj) => `${obj} problemas correctos en grupo`,
  },
  sesiones_completadas: {
    label: 'Completar prácticas',
    icon: CheckSquare,
    dificultad: 2,
    dificultadLabel: 'Medio-bajo',
    dificultadColor: 'bg-blue-100 text-blue-700 border-blue-300',
    descripcionMeta: (obj) => `${obj} prácticas completadas`,
  },
  practicas_sin_errores: {
    label: 'Prácticas con pocos errores',
    icon: Shield,
    dificultad: 3,
    dificultadLabel: 'Medio',
    dificultadColor: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    descripcionMeta: (obj, param) => `${obj} prácticas con máx. ${param ?? '?'} errores`,
  },
  problemas_rapidos: {
    label: 'Problemas rápidos',
    icon: Zap,
    dificultad: 4,
    dificultadLabel: 'Difícil',
    dificultadColor: 'bg-orange-100 text-orange-700 border-orange-300',
    descripcionMeta: (obj, param) => `${obj} problemas en ≤${param ?? '?'} seg c/u`,
  },
  practicas_rapidas: {
    label: 'Prácticas en tiempo',
    icon: Timer,
    dificultad: 5,
    dificultadLabel: 'Muy difícil',
    dificultadColor: 'bg-red-100 text-red-700 border-red-300',
    descripcionMeta: (obj, param) => `${obj} prácticas en ≤${param ?? '?'} minutos`,
  },
};

function estadoBadge(desafio: DesafioEstudiante) {
  if (desafio.grupo_completado || desafio.completado) {
    return <Badge className="bg-green-100 text-green-800 border-green-300">¡Completado!</Badge>;
  }
  if (desafio.esta_expirado) {
    return <Badge variant="destructive">Expirado</Badge>;
  }
  if (desafio.dias_restantes != null) {
    if (desafio.dias_restantes === 0) {
      return <Badge className="bg-amber-100 text-amber-800 border-amber-300">Último día</Badge>;
    }
    if (desafio.dias_restantes <= 2) {
      return <Badge className="bg-amber-100 text-amber-800 border-amber-300">{desafio.dias_restantes}d restantes</Badge>;
    }
    return <Badge variant="outline">{desafio.dias_restantes}d restantes</Badge>;
  }
  return <Badge variant="outline">Sin límite</Badge>;
}

function unidadProgreso(tipo: TipoDesafio): string {
  switch (tipo) {
    case 'problemas_resueltos':  return 'problemas';
    case 'sesiones_completadas': return 'prácticas';
    case 'practicas_sin_errores':return 'prácticas';
    case 'problemas_rapidos':    return 'problemas';
    case 'practicas_rapidas':    return 'prácticas';
  }
}

// ─── Card de un desafío ───────────────────────────────────────────────────────

function DesafioCard({ desafio }: { desafio: DesafioEstudiante }) {
  const meta      = TIPO_META[desafio.tipo] ?? { label: desafio.tipo, icon: Target };
  const Icon      = meta.icon;
  const terminado = desafio.grupo_completado || desafio.completado;
  const unidad    = unidadProgreso(desafio.tipo);

  return (
    <Card className={`transition-shadow hover:shadow-md ${terminado ? 'border-green-300 bg-green-50/30' : ''}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`shrink-0 p-2 rounded-lg ${terminado ? 'bg-green-100' : 'bg-primary/10'}`}>
              {terminado
                ? <CheckCircle2 className="h-5 w-5 text-green-600" />
                : <Icon className="h-5 w-5 text-primary" />
              }
            </div>
            <div className="min-w-0">
              <CardTitle className="text-lg leading-tight">{desafio.nombre}</CardTitle>
              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                <Users className="h-3 w-3 shrink-0" />
                <span className="truncate">{desafio.grupo_nombre}</span>
              </p>
            </div>
          </div>
          <div className="shrink-0">{estadoBadge(desafio)}</div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Descripción */}
        {desafio.descripcion && (
          <p className="text-sm text-muted-foreground">{desafio.descripcion}</p>
        )}

        {/* Tipo + dificultad */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Icon className="h-3.5 w-3.5" />
            {meta.descripcionMeta(desafio.objetivo_cantidad, desafio.parametro_adicional)}
          </span>
          <Badge variant="outline" className={`text-xs ${meta.dificultadColor}`}>
            {'⭐'.repeat(meta.dificultad)} {meta.dificultadLabel}
          </Badge>
        </div>

        {/* Barra de progreso */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-sm font-medium">
            <span>Progreso del grupo</span>
            <span className="tabular-nums text-primary">
              {desafio.progreso_actual} / {desafio.objetivo_cantidad} {unidad}
            </span>
          </div>
          <Progress
            value={desafio.porcentaje}
            className={`h-3 ${terminado ? '[&>div]:bg-green-500' : ''}`}
          />
          <p className="text-sm font-semibold text-right text-primary">{desafio.porcentaje.toFixed(1)}%</p>
        </div>

        {/* Fecha límite */}
        {desafio.fecha_limite && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>
              Límite:{' '}
              {new Date(desafio.fecha_limite).toLocaleDateString('es-CO', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
              })}
            </span>
          </div>
        )}

        {/* Recompensas */}
        {(desafio.recompensa_puntos || desafio.recompensa_texto) && (
          <div className="space-y-1.5">
            {desafio.recompensa_puntos != null && desafio.recompensa_puntos > 0 && (
              <div className="flex items-center gap-1.5 rounded-md bg-yellow-50 border border-yellow-200 px-2.5 py-1.5 text-xs text-yellow-800">
                <Coins className="h-3.5 w-3.5 shrink-0" />
                <span className="font-medium">
                  {terminado ? '¡' : ''}Recompensa: {desafio.recompensa_puntos.toLocaleString()} monedas{terminado ? ' ¡recibidas!' : ' al completar'}
                </span>
              </div>
            )}
            {desafio.recompensa_texto && (
              <div className="flex items-start gap-1.5 rounded-md bg-amber-50 border border-amber-200 px-2.5 py-1.5 text-xs text-amber-800">
                <Gift className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span>{desafio.recompensa_texto}</span>
              </div>
            )}
          </div>
        )}

        {/* Alerta de participación (solo si hay recompensa de monedas y el desafío no terminó) */}
        {!terminado && desafio.recompensa_puntos != null && desafio.recompensa_puntos > 0 && (
          <div className={`flex items-start gap-1.5 rounded-md px-2.5 py-1.5 text-xs border ${
            desafio.califica_recompensa
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-amber-50 border-amber-200 text-amber-800'
          }`}>
            {desafio.califica_recompensa
              ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              : <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            }
            <span>
              {desafio.califica_recompensa
                ? `¡Tu participación está asegurada! (${desafio.mi_sesiones_en_ventana} prácticas completadas)`
                : desafio.sesiones_para_calificar === 1
                  ? 'Practica 1 vez más para calificar para las monedas'
                  : `Practica ${desafio.sesiones_para_calificar} veces más para calificar para las monedas`
              }
            </span>
          </div>
        )}

        {/* Top contribuidores del grupo */}
        {desafio.top_contribuidores.length > 0 && (
          <div className="space-y-1.5 pt-1 border-t">
            <p className="text-xs font-medium flex items-center gap-1 text-muted-foreground">
              <Medal className="h-3.5 w-3.5" />
              Más activos del grupo
            </p>
            <div className="space-y-0.5">
              {desafio.top_contribuidores.map((c, i) => (
                <div key={c.nombre} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className={`font-bold w-4 text-center ${
                      i === 0 ? 'text-yellow-500' : i === 1 ? 'text-slate-400' : i === 2 ? 'text-amber-700' : 'text-muted-foreground'
                    }`}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}
                    </span>
                    <span className="truncate max-w-[130px]">{c.nombre}</span>
                  </span>
                  <span className="text-muted-foreground shrink-0">
                    {c.sesiones} {c.sesiones === 1 ? 'práctica' : 'prácticas'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Página ───────────────────────────────────────────────────────────────────

type Filtro = 'todos' | 'activos' | 'completados' | 'expirados';

export function ChallengesPage() {
  const [filtro, setFiltro] = useState<Filtro>('todos');

  const { data: desafios = [], isLoading, isError } = useQuery({
    queryKey: ['desafios-estudiante'],
    queryFn:  () => studentService.getDesafios(),
    staleTime: 2 * 60 * 1000,
  });

  const filtrados = desafios.filter((d) => {
    const terminado = d.grupo_completado || d.completado;
    if (filtro === 'activos')     return !terminado && !d.esta_expirado;
    if (filtro === 'completados') return terminado;
    if (filtro === 'expirados')   return d.esta_expirado && !terminado;
    return true;
  });

  const n = {
    activos:     desafios.filter((d) => !(d.grupo_completado || d.completado) && !d.esta_expirado).length,
    completados: desafios.filter((d) => d.grupo_completado || d.completado).length,
    expirados:   desafios.filter((d) => d.esta_expirado && !(d.grupo_completado || d.completado)).length,
  };

  const tabs: { key: Filtro; label: string; count: number }[] = [
    { key: 'todos',       label: 'Todos',       count: desafios.length },
    { key: 'activos',     label: 'Activos',     count: n.activos },
    { key: 'completados', label: 'Completados', count: n.completados },
    { key: 'expirados',   label: 'Expirados',   count: n.expirados },
  ];

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex items-center gap-2">
        <Target className="h-6 w-6" />
        <h1 className="text-3xl font-bold">Mis Desafíos</h1>
      </div>

      {/* Tarjetas de resumen */}
      {!isLoading && !isError && desafios.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="text-center">
            <CardContent className="pt-4 pb-3">
              <p className="text-2xl font-bold text-primary">{desafios.length}</p>
              <p className="text-xs text-muted-foreground mt-0.5">Total</p>
            </CardContent>
          </Card>
          <Card className="text-center">
            <CardContent className="pt-4 pb-3">
              <p className="text-2xl font-bold text-green-600">{n.completados}</p>
              <p className="text-xs text-muted-foreground mt-0.5">Completados</p>
            </CardContent>
          </Card>
          <Card className="text-center">
            <CardContent className="pt-4 pb-3">
              <p className="text-2xl font-bold text-blue-600">{n.activos}</p>
              <p className="text-xs text-muted-foreground mt-0.5">En progreso</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filtros tipo pill */}
      {!isLoading && !isError && desafios.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {tabs.map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setFiltro(key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                filtro === key
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background border-border hover:bg-muted'
              }`}
            >
              {label}
              {count > 0 && (
                <span className={`ml-1.5 text-xs ${filtro === key ? 'opacity-75' : 'text-muted-foreground'}`}>
                  ({count})
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Estados ─ cargando */}
      {isLoading && (
        <div className="flex justify-center items-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Estados ─ error */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="font-medium">No se pudieron cargar los desafíos</p>
            <p className="text-sm text-muted-foreground">Intenta recargar la página.</p>
          </CardContent>
        </Card>
      )}

      {/* Estados ─ sin desafíos */}
      {!isLoading && !isError && desafios.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <Trophy className="h-12 w-12 text-muted-foreground/40" />
            <p className="text-lg font-semibold">Sin desafíos por ahora</p>
            <p className="text-sm text-muted-foreground max-w-xs">
              Tu profesor aún no ha creado desafíos para tu grupo. ¡Sigue practicando!
            </p>
          </CardContent>
        </Card>
      )}

      {/* Estados ─ filtro vacío */}
      {!isLoading && !isError && desafios.length > 0 && filtrados.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <Target className="h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No hay desafíos en esta categoría.</p>
          </CardContent>
        </Card>
      )}

      {/* Grid de desafíos — máximo 2 columnas para que los parámetros sean legibles */}
      {!isLoading && !isError && filtrados.length > 0 && (
        <div className="grid gap-5 md:grid-cols-2">
          {filtrados.map((desafio) => (
            <DesafioCard key={desafio.id} desafio={desafio} />
          ))}
        </div>
      )}
    </div>
  );
}
