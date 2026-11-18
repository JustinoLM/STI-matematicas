/**
 * Página de Medallero — Medallas reales del backend.
 * GET /gamification/medals
 *
 * Medallas secretas no obtenidas se muestran como "???" con candado.
 * Medallas secretas obtenidas muestran nombre/descripción real con efecto dorado.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Trophy, Lock, Star, Loader2, Sparkles } from 'lucide-react';
import { studentService, type MedallaItem } from '@/services/studentService';
import { formatearFecha } from '@/lib/fechas';
import { useEstadoNucleo } from '@/hooks/useEstadoNucleo';
import { MedalleroNucleo } from '@/components/nucleo/motivacion/MedalleroNucleo';

// ─── Constantes ───────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, { label: string; emoji: string }> = {
  aprendizaje: { label: 'Por Aprendizaje', emoji: '📚' },
  volumen:     { label: 'Por Volumen',     emoji: '💪' },
  exploracion: { label: 'Por Exploración', emoji: '🗺️' },
  desafios:    { label: 'Por Desafíos',    emoji: '⚔️' },
};

const CATEGORY_ORDER = ['aprendizaje', 'volumen', 'exploracion', 'desafios'];

// ─── Sub-componente: tarjeta de medalla ──────────────────────────────────────

function MedallaCard({
  medalla,
  esDestacada,
  onDestacar,
  onQuitarDestacada,
  loadingDestacada,
}: {
  medalla: MedallaItem;
  esDestacada: boolean;
  onDestacar: (id: number) => void;
  onQuitarDestacada: () => void;
  loadingDestacada: boolean;
}) {
  const esSecretaOculta = medalla.es_secreta && !medalla.obtenida;

  // El emoji viene en imagen_url; si es null, fallback
  const emoji = medalla.imagen_url ?? '🏅';

  if (esSecretaOculta) {
    return (
      <Card className="opacity-50 border-2 border-dashed border-gray-300 bg-gray-50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="text-4xl grayscale">🔒</span>
            <Badge variant="outline" className="text-xs text-gray-400">
              Secreta
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <h3 className="font-bold text-lg mb-2 text-gray-400">???</h3>
          <p className="text-sm text-gray-400 italic">
            Completa ciertos logros para revelar esta medalla.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Medalla secreta revelada (obtenida)
  if (medalla.es_secreta && medalla.obtenida) {
    return (
      <Card className="hover:shadow-xl transition-all border-2 border-yellow-400 bg-gradient-to-br from-yellow-50 to-amber-50 ring-2 ring-yellow-300/50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="text-4xl">{emoji}</span>
            <div className="flex flex-col items-end gap-1">
              <Badge className="bg-yellow-500 text-white text-xs">
                <Sparkles className="h-3 w-3 mr-1" />
                Secreta
              </Badge>
              <Badge variant="default" className="bg-green-500 text-xs">
                ¡Desbloqueada!
              </Badge>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <h3 className="font-bold text-lg mb-2">{medalla.nombre}</h3>
          <p className="text-sm text-gray-600 mb-3">{medalla.descripcion}</p>
          {medalla.fecha_obtencion && (
            <p className="text-xs text-gray-500">
              {formatearFecha(medalla.fecha_obtencion, { day: 'numeric', month: 'long', year: 'numeric' }, 'es-ES')}
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  // Medalla normal
  return (
    <Card
      className={`transition-all ${
        medalla.obtenida
          ? 'hover:shadow-lg border-2 border-yellow-200 bg-gradient-to-br from-white to-yellow-50/30'
          : 'opacity-55 grayscale border border-gray-200'
      }`}
    >
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="text-4xl">{emoji}</span>
          {medalla.obtenida ? (
            <Badge variant="default" className="bg-green-500 text-xs">
              Desbloqueada
            </Badge>
          ) : (
            <Lock className="h-5 w-5 text-gray-400" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <h3 className="font-bold text-lg mb-2">{medalla.nombre}</h3>
        <p className="text-sm text-gray-600 mb-3">{medalla.descripcion}</p>
        {medalla.obtenida && medalla.fecha_obtencion && (
          <p className="text-xs text-gray-500">
            {formatearFecha(medalla.fecha_obtencion, { day: 'numeric', month: 'long', year: 'numeric' }, 'es-ES')}
          </p>
        )}
        {medalla.obtenida && (
          <div className="mt-3">
            {esDestacada ? (
              <Button
                size="sm"
                variant="secondary"
                className="w-full text-xs"
                disabled={loadingDestacada}
                onClick={onQuitarDestacada}
              >
                <Star className="h-3 w-3 mr-1 fill-yellow-400 text-yellow-400" />
                En dashboard
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="w-full text-xs"
                disabled={loadingDestacada}
                onClick={() => onDestacar(medalla.id)}
              >
                <Star className="h-3 w-3 mr-1" />
                Mostrar en dashboard
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function BadgesPage() {
  // Quien practica en el núcleo ve sus medallas nuevas (fase 7b); en decimales, las de siempre
  const { data: estadoNucleo, isLoading: cargandoNucleo } = useEstadoNucleo();
  if (cargandoNucleo) return null;
  if (estadoNucleo?.disponible) return <MedalleroNucleo />;
  return <MedalleroDecimales />;
}

function MedalleroDecimales() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['medallas-estudiante'],
    queryFn: () => studentService.getMedallas(),
    staleTime: 1000 * 60 * 5,
  });

  const destacarMutation = useMutation({
    mutationFn: (medalId: number) => studentService.setMedallaDestacada(medalId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['medallas-estudiante'] }),
  });

  const quitarDestacadaMutation = useMutation({
    mutationFn: () => studentService.quitarMedallaDestacada(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['medallas-estudiante'] }),
  });

  const medallasDestacadaId = data?.medalla_destacada_id ?? null;
  const loadingDestacada = destacarMutation.isPending || quitarDestacadaMutation.isPending;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
      </div>
    );
  }

  const medallas = data?.medallas ?? [];
  const totalObtenidas = data?.medallas_obtenidas ?? 0;
  // Para el progreso, solo contamos las medallas no-secretas (las secretas son bonus)
  const medallasVisibles = medallas.filter(m => !m.es_secreta);
  const totalVisible = medallasVisibles.length;
  const obtenidasVisibles = medallasVisibles.filter(m => m.obtenida).length;
  const porcentaje = totalVisible > 0 ? Math.round((obtenidasVisibles / totalVisible) * 100) : 0;

  // Secretas obtenidas como bonus
  const secretasObtenidas = medallas.filter(m => m.es_secreta && m.obtenida).length;

  // Agrupar por categoría (incluyendo secretas al final de cada grupo)
  const porCategoria = CATEGORY_ORDER.reduce<Record<string, MedallaItem[]>>((acc, cat) => {
    // Primero las normales, luego las secretas
    const normales = medallas.filter(m => m.categoria === cat && !m.es_secreta);
    const secretas = medallas.filter(m => m.categoria === cat && m.es_secreta);
    acc[cat] = [...normales, ...secretas];
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header con barra de progreso */}
      <Card className="bg-gradient-to-r from-yellow-50 to-amber-50 border-2 border-yellow-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <Trophy className="h-8 w-8 text-yellow-600" />
            <div>
              <h1 className="text-2xl font-bold">Medallero</h1>
              <p className="text-sm text-gray-600 font-normal">
                {obtenidasVisibles} de {totalVisible} medallas •{' '}
                {secretasObtenidas > 0 && (
                  <span className="text-yellow-600 font-medium">
                    +{secretasObtenidas} secretas ✨
                  </span>
                )}
              </p>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Progreso general</span>
            <span className="font-bold">{porcentaje}%</span>
          </div>
          <Progress value={porcentaje} className="h-3" />
          {totalObtenidas > 0 && (
            <p className="text-xs text-gray-500 text-right">
              {totalObtenidas} medallas en total desbloqueadas
            </p>
          )}
        </CardContent>
      </Card>

      {/* Medallas por categoría */}
      {CATEGORY_ORDER.map((cat) => {
        const lista = porCategoria[cat] ?? [];
        if (lista.length === 0) return null;

        const cfg = CATEGORY_LABELS[cat];
        const obtenidas = lista.filter(m => m.obtenida).length;
        const normales = lista.filter(m => !m.es_secreta);

        return (
          <div key={cat}>
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <span>{cfg.emoji}</span>
              {cfg.label}
              <span className="text-sm font-normal text-gray-500">
                ({obtenidas}/{normales.length}
                {lista.some(m => m.es_secreta) && (
                  <span className="text-yellow-600"> + secretas</span>
                )})
              </span>
              {cat === 'desafios' && (
                <Star className="h-4 w-4 text-yellow-500" />
              )}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {lista.map((medalla) => (
                <MedallaCard
                  key={medalla.id}
                  medalla={medalla}
                  esDestacada={medallasDestacadaId === medalla.id}
                  onDestacar={(id) => destacarMutation.mutate(id)}
                  onQuitarDestacada={() => quitarDestacadaMutation.mutate()}
                  loadingDestacada={loadingDestacada}
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Sin medallas */}
      {medallas.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            <Trophy className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Aún no hay medallas disponibles.</p>
            <p className="text-sm mt-1">¡Practica para desbloquear la primera!</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
