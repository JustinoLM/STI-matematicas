/**
 * Inventario/Tienda del estudiante
 * Muestra todos los desbloqueables organizados por categoría
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { studentService } from '@/services/studentService';
import {
  Lock,
  ShoppingCart,
  Sparkles,
  Crown,
  Check,
  AlertCircle,
  TrendingUp,
  Music2
} from 'lucide-react';
import {
  getTodosLosDesbloqueables,
  getMusicasPorTema,
  getFondosPorTema,
  type CategoriaDesbloqueable,
  type DesbloquableDetallado,
  type RarezaItem
} from '@/types';
import { FONDOS } from '@/types/shop';
import { useThemeStore } from '@/store/themeStore';

export function ShopPage() {
  const queryClient = useQueryClient();

  // ── Datos reales desde el backend ─────────────────────────────────────────
  const { data: saldo } = useQuery({
    queryKey: ['saldo-estudiante'],
    queryFn: () => studentService.getSaldo(),
    staleTime: 1000 * 60 * 2,
  });

  const { data: perfil } = useQuery({
    queryKey: ['perfil-estudiante'],
    queryFn: () => studentService.getPerfil(),
    staleTime: 1000 * 60 * 5,
  });

  // Catálogo completo de la BD: tiene IDs numéricos y flag poseido
  const { data: catalogo } = useQuery({
    queryKey: ['catalogo-tienda'],
    queryFn: () => studentService.getCatalogo(),
    staleTime: 1000 * 60 * 10,
  });

  // Mapa archivo_referencia → { id_bd, poseido } para lookups O(1)
  const catalogoMap = new Map<string, { id: number; poseido: boolean }>();
  if (catalogo) {
    const todos = [
      ...catalogo.temas,
      ...catalogo.fondos,
      ...catalogo.colores,
      ...catalogo.musicas,
      ...catalogo.efectos,
    ];
    for (const item of todos) {
      if (item.archivo_referencia) {
        catalogoMap.set(item.archivo_referencia, { id: item.id, poseido: item.poseido });
      }
    }
  }

  const puntosDisponibles = saldo?.puntos_totales ?? 0;
  const nivelEstudiante = perfil?.nivel_actual ?? 1;

  // Mutation de compra
  const compraMutation = useMutation({
    mutationFn: (desbloqueableId: number) => studentService.comprarItem(desbloqueableId),
    onSuccess: (data) => {
      if (data.exito) {
        queryClient.invalidateQueries({ queryKey: ['saldo-estudiante'] });
        queryClient.invalidateQueries({ queryKey: ['catalogo-tienda'] });
      }
    },
  });

  // Tema activo del estudiante — determina qué músicas se muestran en la tienda
  const temaActivoId = useThemeStore(s => s.temaActivoId);
  const getTemaActivo = useThemeStore(s => s.getTemaActivo);
  const temaActivo = getTemaActivo();

  // Músicas del tema activo con estado real de la BD
  const musicasDelTemaActivo = getMusicasPorTema(temaActivoId).map(m => ({
    ...m,
    estaDesbloqueado: catalogoMap.get(m.id)?.poseido ?? false,
  }));

  // Fondos del tema activo (narrativos: ilustración, dibujo, estampado)
  const fondosDelTemaActivo = getFondosPorTema(temaActivoId).map(f => ({
    ...f,
    estaDesbloqueado: catalogoMap.get(f.id)?.poseido ?? false,
  }));

  // Fondos del tema Clásico (los 3 genéricos sin temaId)
  const fondosClasicos = FONDOS.filter(f => !f.config?.temaId).map(f => ({
    ...f,
    estaDesbloqueado: catalogoMap.get(f.id)?.poseido ?? false,
  }));

  // Items de shop.ts enriquecidos con el flag estaDesbloqueado desde la BD.
  // Los fondos temáticos solo se muestran en "Todos" si el tema padre está desbloqueado.
  const todosLosItems = getTodosLosDesbloqueables()
    .map(item => ({
      ...item,
      estaDesbloqueado: catalogoMap.get(item.id)?.poseido ?? false,
    }))
    .filter(item => {
      if (item.categoria === 'fondo' && item.config?.temaId) {
        return catalogoMap.get(item.config.temaId)?.poseido ?? false;
      }
      if (item.categoria === 'musica' && item.config?.temaId_musica) {
        return catalogoMap.get(item.config.temaId_musica)?.poseido ?? false;
      }
      return true;
    });

  // Función para obtener el color del badge según la rareza
  const getRarezaColor = (rareza: RarezaItem): string => {
    switch (rareza) {
      case 'comun':
        return 'bg-gray-100 text-gray-700 border-gray-300';
      case 'raro':
        return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'epico':
        return 'bg-purple-100 text-purple-700 border-purple-300';
      case 'legendario':
        return 'bg-yellow-100 text-yellow-700 border-yellow-400';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  // Función para manejar la compra
  const handleComprar = (item: DesbloquableDetallado) => {
    const entrada = catalogoMap.get(item.id);
    if (!entrada) {
      console.warn('Item no encontrado en catálogo de BD:', item.id);
      return;
    }
    compraMutation.mutate(entrada.id);
  };

  // Renderizar un item de la tienda
  const renderItem = (item: DesbloquableDetallado) => {
    const puedeComprar = !item.estaDesbloqueado &&
                         puntosDisponibles >= item.precio &&
                         nivelEstudiante >= item.nivelRequerido;

    const nivelBloqueado = nivelEstudiante < item.nivelRequerido;
    const puntosBloqueado = puntosDisponibles < item.precio;

    return (
      <Card
        key={item.id}
        className={`
          transition-all hover:shadow-lg
          ${item.estaDesbloqueado ? 'border-green-300 bg-green-50/30' : ''}
          ${nivelBloqueado ? 'opacity-60' : ''}
        `}
      >
        <CardHeader>
          <div className="flex items-start justify-between mb-2">
            {/* Icono grande */}
            <div className="text-6xl">{item.icono}</div>

            <div className="flex flex-col gap-1">
              {/* Badge de rareza */}
              <Badge className={`${getRarezaColor(item.rareza)} text-xs`}>
                {item.rareza.toUpperCase()}
              </Badge>

              {/* Estado */}
              {item.estaDesbloqueado && (
                <Badge className="bg-green-100 text-green-700 border-green-300">
                  <Check className="w-3 h-3 mr-1" />
                  Desbloqueado
                </Badge>
              )}

              {item.esGratuito && !item.estaDesbloqueado && (
                <Badge className="bg-blue-100 text-blue-700 border-blue-300">
                  ¡GRATIS!
                </Badge>
              )}
            </div>
          </div>

          <CardTitle className="text-lg">{item.nombre}</CardTitle>
          <CardDescription className="text-sm">
            {item.descripcion}
          </CardDescription>

          {/* Requisitos */}
          <div className="mt-2 space-y-1 text-xs">
            {item.nivelRequerido > 1 && (
              <div className={`flex items-center gap-1 ${nivelBloqueado ? 'text-red-600' : 'text-gray-600'}`}>
                <TrendingUp className="w-3 h-3" />
                <span>Requiere Nivel {item.nivelRequerido}</span>
                {nivelBloqueado && (
                  <span className="text-red-600 font-medium">
                    (Tu nivel: {nivelEstudiante})
                  </span>
                )}
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent>
          <div className="flex flex-col gap-2">
            {/* Precio */}
            <div className="flex items-center gap-2">
              <Sparkles className={`h-5 w-5 ${puntosBloqueado ? 'text-gray-400' : 'text-yellow-600'}`} />
              <span className={`font-bold text-xl ${puntosBloqueado ? 'text-gray-400' : 'text-gray-900'}`}>
                {item.precio}
              </span>
              <span className="text-sm text-gray-500">pts</span>
            </div>

            {/* Botón de acción — ancho completo */}
            {item.estaDesbloqueado ? (
              <Button variant="outline" disabled size="sm" className="w-full">
                <Check className="h-4 w-4 mr-2" />
                En inventario
              </Button>
            ) : nivelBloqueado ? (
              <Button variant="secondary" disabled size="sm" className="w-full">
                <Lock className="h-4 w-4 mr-2" />
                Nivel {item.nivelRequerido} requerido
              </Button>
            ) : item.esGratuito ? (
              <Button
                onClick={() => handleComprar(item)}
                className="w-full bg-green-600 hover:bg-green-700"
                size="sm"
              >
                <Crown className="h-4 w-4 mr-2" />
                Reclamar gratis
              </Button>
            ) : (
              <Button
                onClick={() => handleComprar(item)}
                disabled={!puedeComprar}
                size="sm"
                className="w-full"
              >
                {puntosBloqueado ? (
                  <>
                    <Lock className="h-4 w-4 mr-2" />
                    Faltan {item.precio - puntosDisponibles} pts
                  </>
                ) : (
                  <>
                    <ShoppingCart className="h-4 w-4 mr-2" />
                    Comprar
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  // Filtrar items por categoría (con estado real de la BD)
  const getItemsPorTab = (categoria: CategoriaDesbloqueable | 'todos') => {
    if (categoria === 'todos') return todosLosItems;
    return todosLosItems.filter(item => item.categoria === categoria);
  };

  return (
    <div className="space-y-6">
      {/* Header con puntos disponibles */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Tienda de Desbloqueables</h1>
          <p className="text-muted-foreground">
            Personaliza tu experiencia con temas, colores, música y efectos
          </p>
        </div>

        {/* Card de puntos */}
        <Card className="bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-200">
          <CardContent className="pt-6 pb-4 px-6">
            <div className="flex flex-col items-center gap-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-6 w-6 text-yellow-600" />
                <span className="text-3xl font-bold text-yellow-700">
                  {puntosDisponibles}
                </span>
              </div>
              <span className="text-sm text-gray-600 font-medium">
                Puntos Disponibles
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Información de nivel */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle className="h-4 w-4 text-blue-600" />
            <span className="text-blue-900">
              <strong>Tu nivel actual: {nivelEstudiante}</strong> - Algunos items requieren niveles más altos para desbloquearse.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Tabs por categoría */}
      <Tabs defaultValue="todos" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="todos">
            Todos
          </TabsTrigger>
          <TabsTrigger value="tema">
            🎭 Temas
          </TabsTrigger>
          <TabsTrigger value="fondo">
            🖼️ Fondos
          </TabsTrigger>
          <TabsTrigger value="color">
            🎨 Colores
          </TabsTrigger>
          <TabsTrigger value="musica">
            🎵 Música
          </TabsTrigger>
          <TabsTrigger value="efecto">
            ✨ Efectos
          </TabsTrigger>
        </TabsList>

        {/* Tab: Todos */}
        <TabsContent value="todos">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {todosLosItems.map(renderItem)}
          </div>
        </TabsContent>

        {/* Tab: Temas */}
        <TabsContent value="tema">
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Los temas cambian la narrativa completa de tu experiencia de aprendizaje.
              Cada tema incluye colores, efectos de victoria y una historia única.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {getItemsPorTab('tema').map(renderItem)}
            </div>
          </div>
        </TabsContent>

        {/* Tab: Fondos */}
        <TabsContent value="fondo">
          <div className="space-y-4">
            {/* Descripción contextual según el tema activo */}
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-4">
              <span className="text-xl mt-0.5 flex-shrink-0">🖼️</span>
              <div>
                <p className="text-sm font-medium text-gray-800">
                  Fondos del tema{' '}
                  <span className="text-primary">
                    {temaActivo?.icono} {temaActivo?.nombre}
                  </span>
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {temaActivoId === 'tema-default'
                    ? 'El tema Clásico incluye 3 fondos propios. Desbloquea un tema narrativo para ver sus fondos exclusivos.'
                    : 'Hay 3 fondos disponibles para tu tema. Cada uno tiene un estilo visual diferente.'}
                </p>
              </div>
            </div>

            {temaActivoId === 'tema-default' ? (
              /* Clásico: sus 3 fondos genéricos */
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {fondosClasicos.map(renderItem)}
              </div>
            ) : (
              /* Temas narrativos: 3 slots fijos por tipo */
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(
                  [
                    { tipo: 'ilustracion' as const, etiqueta: 'Ilustración',  subtitulo: 'Escena del tema',   emoji: '🏞️', descripcionBase: 'Ilustración detallada del mundo del tema.' },
                    { tipo: 'dibujo'      as const, etiqueta: 'Dibujo',       subtitulo: 'Arte del tema',     emoji: '🎨', descripcionBase: 'Arte estilo libro ilustrado o cartoon.' },
                    { tipo: 'estampado'   as const, etiqueta: 'Estampado',    subtitulo: 'Patrón del tema',   emoji: '🔷', descripcionBase: 'Patrón con motivos repetidos del tema.' },
                  ]
                ).map(({ tipo, etiqueta, subtitulo, emoji, descripcionBase }) => {
                  const fondo = fondosDelTemaActivo.find(f => f.config?.fondoTipo === tipo);

                  if (!fondo) {
                    return (
                      <Card key={tipo} className="border-dashed opacity-50">
                        <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                          <span className="text-4xl">{emoji}</span>
                          <p className="text-sm font-semibold text-gray-500">{etiqueta}</p>
                          <p className="text-xs text-muted-foreground">No disponible</p>
                        </CardContent>
                      </Card>
                    );
                  }

                  const puedeComprar = !fondo.estaDesbloqueado &&
                                       puntosDisponibles >= fondo.precio &&
                                       nivelEstudiante >= fondo.nivelRequerido;
                  const nivelBloqueado = nivelEstudiante < fondo.nivelRequerido;
                  const puntosBloqueado = puntosDisponibles < fondo.precio;

                  return (
                    <Card
                      key={tipo}
                      className={`
                        transition-all hover:shadow-lg
                        ${fondo.estaDesbloqueado ? 'border-green-300 bg-green-50/30' : ''}
                        ${nivelBloqueado ? 'opacity-60' : ''}
                      `}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-4xl">{fondo.icono}</span>
                            <Badge variant="outline" className="text-xs">
                              {etiqueta}
                            </Badge>
                          </div>
                          <div className="flex flex-col gap-1 items-end">
                            <Badge className={`${getRarezaColor(fondo.rareza)} text-xs`}>
                              {fondo.rareza.toUpperCase()}
                            </Badge>
                            {fondo.estaDesbloqueado && (
                              <Badge className="bg-green-100 text-green-700 border-green-300 text-xs">
                                <Check className="w-3 h-3 mr-1" />
                                Desbloqueado
                              </Badge>
                            )}
                          </div>
                        </div>
                        <CardTitle className="text-base">{fondo.nombre}</CardTitle>
                        <p className="text-xs font-medium text-primary">{subtitulo}</p>
                        <CardDescription className="text-xs mt-1">
                          {fondo.descripcion || descripcionBase}
                        </CardDescription>
                        {nivelBloqueado && (
                          <div className="mt-2 flex items-center gap-1 text-xs text-red-600">
                            <TrendingUp className="w-3 h-3" />
                            <span>Requiere Nivel {fondo.nivelRequerido} (tu nivel: {nivelEstudiante})</span>
                          </div>
                        )}
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2">
                            <Sparkles className={`h-5 w-5 ${puntosBloqueado ? 'text-gray-400' : 'text-yellow-600'}`} />
                            <span className={`font-bold text-xl ${puntosBloqueado ? 'text-gray-400' : 'text-gray-900'}`}>
                              {fondo.precio}
                            </span>
                            <span className="text-sm text-gray-500">pts</span>
                          </div>
                          {fondo.estaDesbloqueado ? (
                            <Button variant="outline" disabled size="sm" className="w-full">
                              <Check className="h-4 w-4 mr-2" />
                              Desbloqueado
                            </Button>
                          ) : nivelBloqueado ? (
                            <Button variant="secondary" disabled size="sm" className="w-full">
                              <Lock className="h-4 w-4 mr-2" />
                              Nivel {fondo.nivelRequerido} requerido
                            </Button>
                          ) : (
                            <Button
                              onClick={() => handleComprar(fondo)}
                              disabled={!puedeComprar}
                              size="sm"
                              className="w-full"
                            >
                              {puntosBloqueado ? (
                                <>
                                  <Lock className="h-4 w-4 mr-2" />
                                  Faltan {fondo.precio - puntosDisponibles} pts
                                </>
                              ) : (
                                <>
                                  <ShoppingCart className="h-4 w-4 mr-2" />
                                  Comprar
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab: Colores */}
        <TabsContent value="color">
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Dale un toque personal con tu color favorito. Algunos colores premium requieren nivel 2.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {getItemsPorTab('color').map(renderItem)}
            </div>
          </div>
        </TabsContent>

        {/* Tab: Música */}
        <TabsContent value="musica">
          <div className="space-y-4">
            {/* Descripción contextual según el tema activo */}
            <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-4">
              <Music2 className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-800">
                  Música del tema{' '}
                  <span className="text-primary">
                    {temaActivo?.icono} {temaActivo?.nombre}
                  </span>
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {temaActivoId === 'tema-default'
                    ? 'El tema Clásico no incluye música. Desbloquea un tema narrativo para acceder a las canciones.'
                    : 'Hay 3 tipos de música disponibles para tu tema. Cada uno se adapta a una forma diferente de estudiar.'}
                </p>
              </div>
            </div>

            {temaActivoId === 'tema-default' ? (
              <Card className="border-dashed border-2 border-gray-200">
                <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                  <span className="text-5xl">🎵</span>
                  <p className="text-sm font-medium text-gray-600">
                    Sin música disponible para el tema Clásico
                  </p>
                  <p className="text-xs text-muted-foreground max-w-xs">
                    Ve a la pestaña <strong>Temas</strong> y desbloquea un tema narrativo
                    (Piratas, Astronautas, Magos…) para acceder a sus 3 canciones.
                  </p>
                </CardContent>
              </Card>
            ) : (
              /* 3 slots fijos: tranquila, energética, ambiente */
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(
                  [
                    {
                      tipo: 'tranquila'  as const,
                      etiqueta: 'Tranquila',
                      subtitulo: 'Para concentrarse',
                      emoji: '🎵',
                      descripcionBase: 'Melodía suave que ayuda a mantener el foco durante los ejercicios.',
                    },
                    {
                      tipo: 'energetica' as const,
                      etiqueta: 'Energética',
                      subtitulo: 'Para motivarse',
                      emoji: '🎸',
                      descripcionBase: 'Ritmo dinámico para mantener el ánimo en los momentos difíciles.',
                    },
                    {
                      tipo: 'ambiente'   as const,
                      etiqueta: 'Ambiente',
                      subtitulo: 'Sonidos del mundo',
                      emoji: '🌿',
                      descripcionBase: 'Sonidos del entorno del tema para sentirte dentro de la aventura.',
                    },
                  ]
                ).map(({ tipo, etiqueta, subtitulo, emoji, descripcionBase }) => {
                  const musica = musicasDelTemaActivo.find(m => m.config?.musicaTipo === tipo);

                  if (!musica) {
                    // Slot vacío — no debería ocurrir si shop.ts está bien configurado
                    return (
                      <Card key={tipo} className="border-dashed opacity-50">
                        <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                          <span className="text-4xl">{emoji}</span>
                          <p className="text-sm font-semibold text-gray-500">{etiqueta}</p>
                          <p className="text-xs text-muted-foreground">No disponible</p>
                        </CardContent>
                      </Card>
                    );
                  }

                  const puedeComprar = !musica.estaDesbloqueado &&
                                       puntosDisponibles >= musica.precio &&
                                       nivelEstudiante >= musica.nivelRequerido;
                  const nivelBloqueado = nivelEstudiante < musica.nivelRequerido;
                  const puntosBloqueado = puntosDisponibles < musica.precio;

                  return (
                    <Card
                      key={tipo}
                      className={`
                        transition-all hover:shadow-lg
                        ${musica.estaDesbloqueado ? 'border-green-300 bg-green-50/30' : ''}
                        ${nivelBloqueado ? 'opacity-60' : ''}
                      `}
                    >
                      <CardHeader>
                        <div className="flex items-start justify-between mb-2">
                          {/* Icono tipo + icono canción */}
                          <div className="flex flex-col items-center gap-1">
                            <span className="text-4xl">{musica.icono}</span>
                            <Badge variant="outline" className="text-xs">
                              {etiqueta}
                            </Badge>
                          </div>

                          <div className="flex flex-col gap-1 items-end">
                            <Badge className={`${getRarezaColor(musica.rareza)} text-xs`}>
                              {musica.rareza.toUpperCase()}
                            </Badge>
                            {musica.estaDesbloqueado && (
                              <Badge className="bg-green-100 text-green-700 border-green-300 text-xs">
                                <Check className="w-3 h-3 mr-1" />
                                Desbloqueada
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* Nombre específico de la canción */}
                        <CardTitle className="text-base">{musica.nombre}</CardTitle>
                        <p className="text-xs font-medium text-primary">{subtitulo}</p>
                        <CardDescription className="text-xs mt-1">
                          {musica.descripcion || descripcionBase}
                        </CardDescription>

                        {nivelBloqueado && (
                          <div className="mt-2 flex items-center gap-1 text-xs text-red-600">
                            <TrendingUp className="w-3 h-3" />
                            <span>Requiere Nivel {musica.nivelRequerido} (tu nivel: {nivelEstudiante})</span>
                          </div>
                        )}
                      </CardHeader>

                      <CardContent>
                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2">
                            <Sparkles className={`h-5 w-5 ${puntosBloqueado ? 'text-gray-400' : 'text-yellow-600'}`} />
                            <span className={`font-bold text-xl ${puntosBloqueado ? 'text-gray-400' : 'text-gray-900'}`}>
                              {musica.precio}
                            </span>
                            <span className="text-sm text-gray-500">pts</span>
                          </div>

                          {musica.estaDesbloqueado ? (
                            <Button variant="outline" disabled size="sm" className="w-full">
                              <Check className="h-4 w-4 mr-2" />
                              Desbloqueada
                            </Button>
                          ) : nivelBloqueado ? (
                            <Button variant="secondary" disabled size="sm" className="w-full">
                              <Lock className="h-4 w-4 mr-2" />
                              Nivel {musica.nivelRequerido} requerido
                            </Button>
                          ) : (
                            <Button
                              onClick={() => handleComprar(musica)}
                              disabled={!puedeComprar}
                              size="sm"
                              className="w-full"
                            >
                              {puntosBloqueado ? (
                                <>
                                  <Lock className="h-4 w-4 mr-2" />
                                  Faltan {musica.precio - puntosDisponibles} pts
                                </>
                              ) : (
                                <>
                                  <ShoppingCart className="h-4 w-4 mr-2" />
                                  Comprar
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab: Efectos */}
        <TabsContent value="efecto">
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Efectos especiales que aparecen cuando resuelves problemas correctamente.
              Los efectos avanzados requieren niveles más altos.
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {getItemsPorTab('efecto').map(renderItem)}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
