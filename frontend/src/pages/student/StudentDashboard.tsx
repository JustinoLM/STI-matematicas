/**
 * Dashboard del estudiante - Pantalla principal.
 */

import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useThemeStore } from '@/store/themeStore';
import { useAuthStore } from '@/store/authStore';
import { studentService } from '@/services/studentService';
import {
  BookOpen,
  ShoppingBag,
  Trophy,
  TrendingUp,
  Users,
  Clapperboard,
  Settings,
  Loader2,
  ClipboardList,
  PlayCircle,
  Trash2,
  ChevronRight,
} from 'lucide-react';
import type { SesionActivaResponse } from '@/services/studentService';

export function StudentDashboard() {
  const navigate = useNavigate();
  const { temaActivoId, colorActivoId } = useThemeStore();
  void useAuthStore(s => s.nombreCompleto); // suscribir para re-render al cambiar nombre

  // Mensaje motivacional LLM — queryKey incluye fecha Y temaActivoId para que al
  // cambiar de tema se cargue un mensaje nuevo en vez de servir el del tema anterior.
  const today = new Date().toISOString().split('T')[0];
  const { data: mensajeLLM } = useQuery({
    queryKey: ['mensaje-dashboard', today, temaActivoId],
    queryFn: () => studentService.getMensajeMotivacional('dashboard'),
    staleTime: 1000 * 60 * 60 * 12, // 12 horas por (día, tema)
    retry: false,
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  void colorActivoId; // asegurar re-render al cambiar color (temaActivoId ya se usa arriba)

  const cardGlow = {
    boxShadow: '0 0 0 2px hsl(var(--primary) / 0.35), 0 4px 24px hsl(var(--primary) / 0.40)',
  } as React.CSSProperties;

  const cardGlowHover = {
    boxShadow: '0 0 0 3px hsl(var(--primary) / 0.6), 0 8px 36px hsl(var(--primary) / 0.55)',
  } as React.CSSProperties;

  // ── Datos reales desde el backend ─────────────────────────────────────────
  const { data: perfil, isLoading: loadingPerfil } = useQuery({
    queryKey: ['perfil-estudiante'],
    queryFn: () => studentService.getPerfil(),
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  const { data: saldo, isLoading: loadingSaldo } = useQuery({
    queryKey: ['saldo-estudiante'],
    queryFn: () => studentService.getSaldo(),
    staleTime: 1000 * 60 * 2, // 2 minutos
  });

  const { data: medallas } = useQuery({
    queryKey: ['medallas-estudiante'],
    queryFn: () => studentService.getMedallas(),
    staleTime: 1000 * 60 * 10,
  });

  // ── Sesión activa (recuperación) ───────────────────────────────────────────
  const queryClient = useQueryClient();
  const { data: sesionActiva, isLoading: loadingSesion } = useQuery<SesionActivaResponse | null>({
    queryKey: ['sesion-activa'],
    queryFn: () => studentService.getSesionActiva(),
    staleTime: 1000 * 30, // refrescar cada 30s
    retry: false,
  });

  const retomarMutation = useMutation({
    mutationFn: (sesionId: number) => Promise.resolve(sesionId), // solo navegamos
    onSuccess: (sesionId: number) => {
      navigate('/student/practice', { state: { retomar: true, sesionId } });
    },
  });

  const descartarMutation = useMutation({
    mutationFn: (sesionId: number) => studentService.descartarSesion(sesionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sesion-activa'] });
    },
  });

  // ── Valores derivados ──────────────────────────────────────────────────────
  const nivel = perfil?.nivel_actual ?? '-';
  const puntos = saldo?.puntos_totales ?? 0;
  const precision = perfil ? Math.round(perfil.precision_ultimos_15 * 100) : 0;
  const cantMedallas = medallas?.medallas_obtenidas ?? 0;
  const medallaDestacada = medallas
    ? (medallas.medalla_destacada_id
        ? medallas.medallas.find(m => m.id === medallas.medalla_destacada_id) ?? null
        : medallas.medallas.find(m => m.obtenida) ?? null)
    : null;

  const textoMotivacion = perfil
    ? precision >= 80
      ? '¡Sigue así, estás haciendo un gran trabajo!'
      : precision >= 60
        ? '¡Buen esfuerzo! Cada práctica te hace más fuerte.'
        : '¡Tú puedes! La práctica constante lleva al éxito.'
    : '¡Bienvenido! Empieza una práctica para avanzar.';

  const isLoading = loadingPerfil || loadingSaldo;

  // ── Diagnóstico completado ─────────────────────────────────────────────────
  const diagnosticoCompletado = perfil?.diagnostico_completado ?? true; // true mientras carga (no interrumpir UX)

  // ── Post-test ──────────────────────────────────────────────────────────────
  const { data: postTestEstado } = useQuery({
    queryKey: ['post-test-estado'],
    queryFn: () => studentService.getPostTestEstado(),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
  const postTestPendiente = (postTestEstado?.activo ?? false) && !(postTestEstado?.completado ?? true);

  // ── Navegación ─────────────────────────────────────────────────────────────
  const navigationCards = [
    { title: 'Práctica',       description: 'Resolver problemas',    icon: BookOpen,   path: '/student/practice',   color: 'bg-blue-500'   },
    { title: 'Inventario',     description: 'Mis desbloqueables',    icon: ShoppingBag,path: '/student/inventory',  color: 'bg-purple-500' },
    { title: 'Progreso',       description: 'Ver estadísticas',      icon: TrendingUp, path: '/student/progress',   color: 'bg-green-500'  },
    { title: 'Desafío Grupal', description: 'Colaborar con tu grupo',icon: Users,      path: '/student/challenges', color: 'bg-red-500'    },
  ];

  const handleNavegacion = (path: string) => {
    // Post-test pendiente → redirigir al post-test
    if (path === '/student/practice' && postTestPendiente) {
      navigate('/student/post-test');
    // Diagnóstico no completado → redirigir al diagnóstico
    } else if (path === '/student/practice' && !diagnosticoCompletado) {
      navigate('/student/diagnostic');
    } else {
      navigate(path);
    }
  };

  const secondaryActions = [
    { title: 'Animaciones', icon: Clapperboard, path: '/student/animaciones' },
    { title: 'Editar',      icon: Settings,     path: '/student/settings' },
  ];

  return (
    <div className="space-y-4">
      {/* Banner de post-test pendiente (tiene prioridad sobre diagnóstico) */}
      {postTestPendiente && (
        <Card
          className="cursor-pointer border-2 border-orange-500 bg-orange-50 hover:bg-orange-100 transition-colors"
          onClick={() => navigate('/student/post-test')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-orange-500 text-white flex-shrink-0">
                <ClipboardList className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <p className="font-bold text-base text-orange-800">Evaluación final disponible</p>
                <p className="text-sm text-orange-700">
                  Tu profesor ha activado la evaluación final. Complétala para ver cuánto has mejorado.
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-orange-500 flex-shrink-0" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Banner de diagnóstico pendiente */}
      {!loadingPerfil && !diagnosticoCompletado && (
        <Card
          className="cursor-pointer border-2 border-primary bg-primary/5 hover:bg-primary/10 transition-colors"
          onClick={() => navigate('/student/diagnostic')}
        >
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-primary text-primary-foreground flex-shrink-0">
                <ClipboardList className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <p className="font-bold text-base">Completa tu prueba diagnóstica</p>
                <p className="text-sm text-muted-foreground">
                  Antes de practicar, necesitamos conocer tu nivel actual. ¡Solo son 8 preguntas!
                </p>
              </div>
              <span className="text-sm font-medium text-primary whitespace-nowrap">
                Comenzar →
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Banner de práctica incompleta */}
      {!loadingSesion && sesionActiva && (
        <Card className="border-2 border-amber-400 bg-amber-50">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="p-3 rounded-lg bg-amber-500 text-white flex-shrink-0">
                <PlayCircle className="h-6 w-6" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-base text-amber-900">Tienes una práctica incompleta</p>
                <p className="text-sm text-amber-700">
                  Completaste {sesionActiva.problemas_completados} de {sesionActiva.cantidad_problemas} problemas
                  hace {sesionActiva.minutos_transcurridos} min. ¡Puedes continuar desde donde la dejaste!
                </p>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button
                  size="sm"
                  className="bg-amber-500 hover:bg-amber-600 text-white"
                  onClick={() => retomarMutation.mutate(sesionActiva.sesion_id)}
                  disabled={descartarMutation.isPending}
                >
                  Continuar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-amber-400 text-amber-700 hover:bg-amber-100"
                  onClick={() => descartarMutation.mutate(sesionActiva.sesion_id)}
                  disabled={descartarMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Header con texto motivacional */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50" style={cardGlow}>
        <CardContent className="pt-4 pb-4">
          <div className="text-center">
            <p className="text-2xl font-medium text-gray-700">
              {mensajeLLM ?? textoMotivacion}
            </p>
            <div className="mt-2 flex justify-center gap-6">
              <div className="text-center">
                {isLoading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-blue-400 mx-auto" />
                ) : (
                  <p className="text-2xl font-bold text-blue-600">Nivel {nivel}</p>
                )}
                <p className="text-xs text-gray-600">De 5 niveles</p>
              </div>
              <div className="text-center">
                {loadingSaldo ? (
                  <Loader2 className="h-6 w-6 animate-spin text-yellow-400 mx-auto" />
                ) : (
                  <p className="text-2xl font-bold text-yellow-600">{puntos.toLocaleString()}</p>
                )}
                <p className="text-xs text-gray-600">Puntos</p>
              </div>
              <div className="text-center">
                {loadingPerfil ? (
                  <Loader2 className="h-6 w-6 animate-spin text-purple-400 mx-auto" />
                ) : (
                  <p className="text-2xl font-bold text-purple-600">{precision}%</p>
                )}
                <p className="text-xs text-gray-600">Precisión</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grid principal de navegación */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Columna izquierda: Cards en cuadrícula 2x2 */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-8">
          {navigationCards.map((card) => {
            const Icon = card.icon;
            return (
              <Card
                key={card.path}
                className="cursor-pointer transition-all hover:scale-105"
                style={cardGlow}
                onMouseEnter={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlowHover)}
                onMouseLeave={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlow)}
                onClick={() => handleNavegacion(card.path)}
              >
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{card.title}</span>
                    <div className={`p-3 rounded-lg ${card.color}`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                    <p className="text-gray-500 text-sm">{card.description}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Columna derecha: Card de Medallero */}
        <Card
          className="cursor-pointer transition-all hover:scale-105 ring-2 ring-yellow-400 lg:row-span-2"
          style={cardGlow}
          onMouseEnter={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlowHover)}
          onMouseLeave={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlow)}
          onClick={() => navigate('/student/badges')}
        >
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Medallero</span>
              <div className="p-3 rounded-lg bg-yellow-500">
                <Trophy className="h-6 w-6 text-white" />
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-4">
              <div className="w-24 h-24 bg-gradient-to-br from-yellow-100 to-amber-100 rounded-full flex items-center justify-center shadow-lg">
                <span className="text-3xl">
                  {medallaDestacada
                    ? (medallaDestacada.imagen_url ?? '🏅')
                    : '⭐'}
                </span>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-bold mb-2">
                  {medallaDestacada ? medallaDestacada.nombre : 'Sin medallas aún'}
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  {medallaDestacada ? medallaDestacada.descripcion : 'Completa prácticas para ganar medallas'}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <Trophy className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm font-medium text-gray-700">
                    {cantMedallas} medallas desbloqueadas
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Acciones secundarias */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {secondaryActions.map((action) => {
          const Icon = action.icon;
          return (
            <Card
              key={action.path}
              className="cursor-pointer hover:bg-gray-50 transition-colors"
              style={cardGlow}
              onMouseEnter={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlowHover)}
              onMouseLeave={e => Object.assign((e.currentTarget as HTMLElement).style, cardGlow)}
              onClick={() => navigate(action.path)}
            >
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5 text-gray-600" />
                  <span className="font-medium">{action.title}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
