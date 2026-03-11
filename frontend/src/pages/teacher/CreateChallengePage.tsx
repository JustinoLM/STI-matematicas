/**
 * Página para crear nuevos desafíos grupales.
 *
 * Soporta 5 tipos ordenados por dificultad, recompensa física o monedas,
 * y muestra sugerencias de cantidad de monedas según el tipo elegido.
 */

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Plus, Target, Star, BookOpen, CheckSquare,
  Shield, Zap, Timer, Trophy, Coins, Info,
} from 'lucide-react';
import { teacherService } from '@/services/teacherService';
import { queryClient } from '@/lib/queryClient';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import type { TipoDesafioGrupal } from '@/types';

// ─── Metadatos de cada tipo ───────────────────────────────────────────────────

interface TipoMeta {
  label: string;
  descripcion: string;
  icono: React.ComponentType<{ className?: string }>;
  dificultad: number;
  dificultadLabel: string;
  dificultadColor: string;
  tieneParam: boolean;
  labelObjetivo: string;
  placeholderObjetivo: string;
  labelParam?: string;
  placeholderParam?: string;
  unidad: string;
  puntosBase: number;
}

const TIPOS: Record<TipoDesafioGrupal, TipoMeta> = {
  problemas_resueltos: {
    label: 'Resolver X problemas en grupo',
    descripcion: 'El grupo debe resolver en total X problemas correctos entre todos.',
    icono: BookOpen,
    dificultad: 1,
    dificultadLabel: 'Fácil',
    dificultadColor: 'bg-green-100 text-green-700 border-green-300',
    tieneParam: false,
    labelObjetivo: 'Número de problemas a resolver',
    placeholderObjetivo: 'ej. 100',
    unidad: 'problemas',
    puntosBase: 200,
  },
  sesiones_completadas: {
    label: 'Completar X prácticas',
    descripcion: 'El grupo debe completar en total X sesiones de práctica entre todos.',
    icono: CheckSquare,
    dificultad: 2,
    dificultadLabel: 'Medio-bajo',
    dificultadColor: 'bg-blue-100 text-blue-700 border-blue-300',
    tieneParam: false,
    labelObjetivo: 'Número de prácticas a completar',
    placeholderObjetivo: 'ej. 20',
    unidad: 'prácticas',
    puntosBase: 350,
  },
  practicas_sin_errores: {
    label: 'X prácticas con máximo Y errores',
    descripcion: 'El grupo debe completar X prácticas donde cada sesión tenga como máximo Y respuestas incorrectas.',
    icono: Shield,
    dificultad: 3,
    dificultadLabel: 'Medio',
    dificultadColor: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    tieneParam: true,
    labelObjetivo: 'Número de prácticas a completar',
    placeholderObjetivo: 'ej. 10',
    labelParam: 'Máximo de errores por práctica (Y)',
    placeholderParam: 'ej. 3',
    unidad: 'prácticas',
    puntosBase: 550,
  },
  problemas_rapidos: {
    label: 'X problemas en Y segundos o menos por problema',
    descripcion: 'El grupo debe resolver X problemas correctos en sesiones donde el promedio sea ≤ Y segundos por problema.',
    icono: Zap,
    dificultad: 4,
    dificultadLabel: 'Difícil',
    dificultadColor: 'bg-orange-100 text-orange-700 border-orange-300',
    tieneParam: true,
    labelObjetivo: 'Número de problemas correctos rápidos',
    placeholderObjetivo: 'ej. 50',
    labelParam: 'Tiempo máximo por problema (Y) en segundos',
    placeholderParam: 'ej. 30',
    unidad: 'problemas rápidos',
    puntosBase: 800,
  },
  practicas_rapidas: {
    label: 'X prácticas en Y minutos o menos',
    descripcion: 'El grupo debe completar X sesiones de práctica en ≤ Y minutos cada una.',
    icono: Timer,
    dificultad: 5,
    dificultadLabel: 'Muy difícil',
    dificultadColor: 'bg-red-100 text-red-700 border-red-300',
    tieneParam: true,
    labelObjetivo: 'Número de prácticas a completar en tiempo',
    placeholderObjetivo: 'ej. 5',
    labelParam: 'Tiempo máximo por práctica (Y) en minutos',
    placeholderParam: 'ej. 15',
    unidad: 'prácticas en tiempo',
    puntosBase: 1100,
  },
};

/** Monedas sugeridas = base del tipo × raíz del objetivo (redondeado a 50 más cercano). */
function calcularPuntosSugeridos(tipo: TipoDesafioGrupal, objetivo: number): number {
  const base = TIPOS[tipo].puntosBase;
  const factor = Math.max(1, Math.ceil(Math.sqrt(objetivo)));
  return Math.round((base * factor) / 50) * 50;
}

// ─── Componente ───────────────────────────────────────────────────────────────

export default function CreateChallengePage() {
  const navigate = useNavigate();

  const [nombre, setNombre]                         = useState('');
  const [descripcion, setDescripcion]               = useState('');
  const [tipo, setTipo]                             = useState<TipoDesafioGrupal>('problemas_resueltos');
  const [objetivoCantidad, setObjetivoCantidad]     = useState('');
  const [parametroAdicional, setParametroAdicional] = useState('');
  const [tipoRecompensa, setTipoRecompensa]         = useState<'texto' | 'puntos' | 'ambos'>('puntos');
  const [recompensaTexto, setRecompensaTexto]       = useState('');
  const [recompensaPuntos, setRecompensaPuntos]     = useState('');
  const [fechaLimite, setFechaLimite]               = useState('');
  const [gruposIds, setGruposIds]                   = useState<number[]>([]);

  const meta    = TIPOS[tipo];
  const objNum  = parseInt(objetivoCantidad) || 0;
  const sugerido = objNum > 0 ? calcularPuntosSugeridos(tipo, objNum) : meta.puntosBase;

  const { data: grupos } = useQuery({
    queryKey: ['teacher', 'groups'],
    queryFn: () => teacherService.getGrupos(),
  });

  const crearMutation = useMutation({
    mutationFn: (data: Parameters<typeof teacherService.crearDesafio>[0]) =>
      teacherService.crearDesafio(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teacher', 'challenges'] });
      navigate('/teacher/challenges');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre || !objetivoCantidad || gruposIds.length === 0) return;
    if (meta.tieneParam && !parametroAdicional) return;

    crearMutation.mutate({
      nombre,
      descripcion: descripcion || undefined,
      tipo,
      objetivo_cantidad: parseInt(objetivoCantidad),
      parametro_adicional: meta.tieneParam ? parseInt(parametroAdicional) : undefined,
      recompensa_texto:
        (tipoRecompensa === 'texto' || tipoRecompensa === 'ambos') && recompensaTexto
          ? recompensaTexto : undefined,
      recompensa_puntos:
        (tipoRecompensa === 'puntos' || tipoRecompensa === 'ambos') && recompensaPuntos
          ? parseInt(recompensaPuntos) : undefined,
      grupos_ids: gruposIds,
      fecha_limite: fechaLimite || undefined,
    });
  };

  const toggleGrupo = (id: number) =>
    setGruposIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/teacher/challenges">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Desafíos
          </Button>
        </Link>
        <h1 className="text-3xl font-bold mt-2">Crear Nuevo Desafío</h1>
        <p className="text-muted-foreground">Configura un desafío grupal para motivar a tus estudiantes</p>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6">

        {/* ── Tipo de desafío ────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Tipo de Desafío</CardTitle>
            <p className="text-sm text-muted-foreground">
              Ordenados de más fácil (⭐) a más difícil (⭐⭐⭐⭐⭐)
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {(Object.entries(TIPOS) as [TipoDesafioGrupal, TipoMeta][]).map(([key, m]) => {
              const Icono = m.icono;
              const activo = tipo === key;
              return (
                <label
                  key={key}
                  className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                    activo
                      ? 'border-primary bg-primary/5 ring-1 ring-primary'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="tipo"
                    value={key}
                    checked={activo}
                    onChange={() => { setTipo(key); setParametroAdicional(''); }}
                    className="mt-1 h-4 w-4"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Icono className="h-4 w-4 shrink-0" />
                      <span className="font-medium">{m.label}</span>
                      <Badge variant="outline" className={`text-xs ${m.dificultadColor}`}>
                        {'⭐'.repeat(m.dificultad)} {m.dificultadLabel}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{m.descripcion}</p>
                  </div>
                </label>
              );
            })}
          </CardContent>
        </Card>

        {/* ── Información básica ─────────────────────────────────────── */}
        <Card>
          <CardHeader><CardTitle>Información del Desafío</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="nombre">Nombre del Desafío *</Label>
              <Input
                id="nombre"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="ej. ¡Semana de los 100 problemas!"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="descripcion">Descripción (opcional)</Label>
              <Textarea
                id="descripcion"
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                placeholder="Agrega detalles motivadores sobre el desafío"
                rows={2}
              />
            </div>

            <div className={`grid gap-4 ${meta.tieneParam ? 'md:grid-cols-2' : ''}`}>
              <div className="space-y-2">
                <Label htmlFor="objetivo">{meta.labelObjetivo} *</Label>
                <Input
                  id="objetivo"
                  type="number"
                  min="1"
                  value={objetivoCantidad}
                  onChange={(e) => setObjetivoCantidad(e.target.value)}
                  placeholder={meta.placeholderObjetivo}
                  required
                />
              </div>
              {meta.tieneParam && (
                <div className="space-y-2">
                  <Label htmlFor="param">{meta.labelParam} *</Label>
                  <Input
                    id="param"
                    type="number"
                    min="1"
                    value={parametroAdicional}
                    onChange={(e) => setParametroAdicional(e.target.value)}
                    placeholder={meta.placeholderParam}
                    required
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="fecha_limite">Fecha Límite (opcional)</Label>
              <Input
                id="fecha_limite"
                type="date"
                value={fechaLimite}
                min={new Date().toISOString().split('T')[0]}
                onChange={(e) => setFechaLimite(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* ── Recompensa ─────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Recompensa al Completar</CardTitle>
            <p className="text-sm text-muted-foreground">
              Elige cómo premiar al grupo cuando logre el objetivo
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              {(
                [
                  { key: 'puntos', label: 'Monedas',   icon: Coins  },
                  { key: 'texto',  label: 'Física',    icon: Trophy  },
                  { key: 'ambos',  label: 'Ambas',     icon: Star    },
                ] as const
              ).map(({ key, label, icon: Icono }) => (
                <label
                  key={key}
                  className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border cursor-pointer transition-all text-sm ${
                    tipoRecompensa === key
                      ? 'border-primary bg-primary/5 ring-1 ring-primary font-medium'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="tipo_recompensa"
                    value={key}
                    checked={tipoRecompensa === key}
                    onChange={() => setTipoRecompensa(key)}
                    className="sr-only"
                  />
                  <Icono className="h-5 w-5" />
                  {label}
                </label>
              ))}
            </div>

            {(tipoRecompensa === 'puntos' || tipoRecompensa === 'ambos') && (
              <div className="space-y-2">
                <Label htmlFor="recompensa_puntos">
                  Monedas para cada estudiante del grupo
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="recompensa_puntos"
                    type="number"
                    min="0"
                    step="50"
                    value={recompensaPuntos}
                    onChange={(e) => setRecompensaPuntos(e.target.value)}
                    placeholder={String(sugerido)}
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setRecompensaPuntos(String(sugerido))}
                    className="shrink-0 whitespace-nowrap"
                  >
                    Usar sugerido ({sugerido.toLocaleString()})
                  </Button>
                </div>
                <div className="flex items-start gap-1.5 rounded-md bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-800">
                  <Info className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  <span>
                    Para dificultad <strong>{meta.dificultadLabel}</strong> el rango orientativo es:{' '}
                    ⭐ 200–500 · ⭐⭐ 300–700 · ⭐⭐⭐ 500–1 000 · ⭐⭐⭐⭐ 700–1 500 · ⭐⭐⭐⭐⭐ 1 000–2 500 monedas.
                    Las monedas se otorgan automáticamente a cada estudiante del grupo al completar.
                  </span>
                </div>
              </div>
            )}

            {(tipoRecompensa === 'texto' || tipoRecompensa === 'ambos') && (
              <div className="space-y-2">
                <Label htmlFor="recompensa_texto">Descripción de la recompensa física</Label>
                <Input
                  id="recompensa_texto"
                  value={recompensaTexto}
                  onChange={(e) => setRecompensaTexto(e.target.value)}
                  placeholder="ej. 10 minutos de tiempo libre, stickers, etc."
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Grupos ─────────────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Grupos Participantes *</CardTitle>
              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm"
                  onClick={() => grupos && setGruposIds(grupos.map((g) => g.id))}>
                  Todos
                </Button>
                <Button type="button" variant="outline" size="sm"
                  onClick={() => setGruposIds([])}>
                  Ninguno
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {grupos && grupos.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {grupos.map((grupo) => (
                  <label
                    key={grupo.id}
                    className={`flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                      gruposIds.includes(grupo.id)
                        ? 'border-primary bg-primary/5'
                        : 'border-muted hover:border-muted-foreground/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={gruposIds.includes(grupo.id)}
                      onChange={() => toggleGrupo(grupo.id)}
                      className="h-4 w-4"
                    />
                    <div>
                      <p className="font-medium">{grupo.nombre}</p>
                      <p className="text-sm text-muted-foreground">
                        {grupo.cantidad_estudiantes} estudiantes
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Target className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground">No tienes grupos creados</p>
                <Link to="/teacher/groups/new">
                  <Button variant="link">
                    <Plus className="mr-2 h-4 w-4" />Crear primer grupo
                  </Button>
                </Link>
              </div>
            )}
            {gruposIds.length === 0 && grupos && grupos.length > 0 && (
              <p className="text-sm text-red-500 mt-3">* Debes seleccionar al menos un grupo</p>
            )}
          </CardContent>
        </Card>

        {/* Botones */}
        <div className="flex gap-3 justify-end">
          <Link to="/teacher/challenges">
            <Button type="button" variant="outline">Cancelar</Button>
          </Link>
          <Button
            type="submit"
            disabled={
              !nombre ||
              !objetivoCantidad ||
              (meta.tieneParam && !parametroAdicional) ||
              gruposIds.length === 0 ||
              crearMutation.isPending
            }
          >
            {crearMutation.isPending ? 'Creando...' : 'Crear Desafío'}
          </Button>
        </div>

        {crearMutation.isError && (
          <Card className="border-red-500">
            <CardContent className="p-4">
              <p className="text-sm text-red-500">Error al crear el desafío. Intenta nuevamente.</p>
            </CardContent>
          </Card>
        )}
      </form>
    </div>
  );
}
