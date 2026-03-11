/**
 * Sistema de Desbloqueables para la Tienda
 * Incluye temas narrativos, fondos, colores, música y efectos especiales
 */

export type CategoriaDesbloqueable =
  | 'tema'      // 7 narrativas (500 pts c/u, 1 gratis por defecto)
  | 'fondo'     // 3 fondos por tema (75 pts c/u)
  | 'color'     // 12 colores (50 pts c/u)
  | 'musica'    // 3 músicas por tema (100 pts c/u, req. nivel 3)
  | 'efecto';   // 5 efectos (100-150 pts)

export type RarezaItem = 'comun' | 'raro' | 'epico' | 'legendario';

export interface Desbloqueable {
  id: string;
  nombre: string;
  descripcion: string;
  categoria: CategoriaDesbloqueable;
  precio: number;
  nivelRequerido: number;
  rareza: RarezaItem;
  icono?: string;
  preview?: string;
  estaDesbloqueado: boolean;
  esGratuito: boolean;

  config?: {
    // Para temas
    colorPrimario?: string;
    colorSecundario?: string;
    colorAccent?: string;
    efectoVictoria?: string;
    vocabulario?: {
      correcto: string;
      incorrecto: string;
      nivel: string;
      bienvenida: string;
    };

    // Para fondos — pertenecen a un tema y tienen un índice (1, 2, 3)
    temaId?: string;       // A qué tema pertenece este fondo
    fondoIndex?: number;   // 1, 2 o 3 dentro del tema
    fondoTipo?: 'ilustracion' | 'dibujo' | 'estampado'; // Tipo semántico del fondo
    urlImagen?: string;
    patron?: 'solido' | 'gradiente' | 'patron';

    // Para colores
    colorHex?: string;
    aplicaA?: 'interfaz' | 'problemas' | 'ambos';

    // Para música — pertenecen a un tema y tienen un índice (1, 2, 3)
    temaId_musica?: string;  // A qué tema pertenece esta música
    musicaIndex?: number;    // 1, 2 o 3 dentro del tema
    musicaTipo?: 'tranquila' | 'energetica' | 'ambiente'; // Tipo semántico de la música
    urlAudio?: string;
    duracion?: number;
    tipo?: 'energica' | 'concentracion' | 'aventura'; // Mantenido por compatibilidad

    // Para efectos
    animacion?: string;
    duracionMs?: number;
    sonido?: string;
  };
}

// ============================================================
// TEMAS NARRATIVOS (7 total: 1 default gratis + 6 narrativos)
// ============================================================
export const TEMAS: Desbloqueable[] = [
  {
    id: 'tema-default',
    nombre: 'Clásico Matemático',
    descripcion: 'El tema limpio y sin distracciones. Perfecto si prefieres enfocarte solo en las matemáticas.',
    categoria: 'tema',
    precio: 0,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '📐',
    estaDesbloqueado: true,
    esGratuito: true,
    config: {
      colorPrimario: '#171717',
      colorSecundario: '#404040',
      colorAccent: '#F3F4F6',
      efectoVictoria: 'estrellas',
      vocabulario: {
        correcto: '¡Correcto! ¡Excelente trabajo!',
        incorrecto: 'Inténtalo de nuevo, tú puedes.',
        nivel: 'Nivel',
        bienvenida: '¡Bienvenido al Sistema de Tutoría!',
      },
    },
  },
  {
    id: 'tema-piratas',
    nombre: 'Piratas de los Mares',
    descripcion: 'Navega en alta mar, reparte botines y demuestra que los decimales no tienen secretos para un verdadero Capitán Pirata.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 1,
    rareza: 'raro',
    icono: '🏴‍☠️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#92400E',
      colorSecundario: '#451A03',
      colorAccent: '#FEF3C7',
      efectoVictoria: 'cannonballs',
      vocabulario: {
        correcto: '¡Arrr! ¡Excelente cálculo, marinero!',
        incorrecto: '¡Los piratas no se rinden! Inténtalo de nuevo.',
        nivel: 'Rango Pirata',
        bienvenida: '¡Bienvenido a bordo, Capitán!',
      },
    },
  },
  {
    id: 'tema-astronautas',
    nombre: 'Astronautas de la Estación Decimal',
    descripcion: 'Mezcla combustibles, calcula órbitas y explora el universo de los decimales.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 1,
    rareza: 'raro',
    icono: '🚀',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#7C3AED',
      colorSecundario: '#4C1D95',
      colorAccent: '#EDE9FE',
      efectoVictoria: 'shooting-stars',
      vocabulario: {
        correcto: '¡Misión cumplida, comandante!',
        incorrecto: 'Recalculando trayectoria... inténtalo de nuevo.',
        nivel: 'Rango Espacial',
        bienvenida: '¡Bienvenido a la Estación Decimal, Comandante!',
      },
    },
  },
  {
    id: 'tema-magos',
    nombre: 'Magos de la Academia Numérica',
    descripcion: 'Prepara pociones, calcula hechizos y domina la magia de los números decimales.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🧙',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#7E22CE',
      colorSecundario: '#3B0764',
      colorAccent: '#F5F3FF',
      efectoVictoria: 'magic-sparks',
      vocabulario: {
        correcto: '¡Conjuro perfecto, joven mago!',
        incorrecto: 'El hechizo falló... vuelve a intentarlo.',
        nivel: 'Rango Mágico',
        bienvenida: '¡Bienvenido a la Academia Numérica, aprendiz!',
      },
    },
  },
  {
    id: 'tema-caballeros',
    nombre: 'Caballeros del Reino Decimal',
    descripcion: 'Reparte provisiones, mide distancias y defiende el reino con tus habilidades matemáticas.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '⚔️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#DC2626',
      colorSecundario: '#7F1D1D',
      colorAccent: '#FEF2F2',
      efectoVictoria: 'sword-slash',
      vocabulario: {
        correcto: '¡Honor al campeón matemático!',
        incorrecto: 'Un caballero persevera. ¡Inténtalo de nuevo!',
        nivel: 'Rango de Caballero',
        bienvenida: '¡Bienvenido al Reino Decimal, noble caballero!',
      },
    },
  },
  {
    id: 'tema-vaqueros',
    nombre: 'Vaqueros del Viejo Oeste',
    descripcion: 'Comercia ganado, mide terrenos y conviértete en el mejor calculador del Lejano Oeste.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🤠',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#B45309',
      colorSecundario: '#78350F',
      colorAccent: '#FFFBEB',
      efectoVictoria: 'lasso-spin',
      vocabulario: {
        correcto: '¡Yeehaw! ¡Cálculo certero, vaquero!',
        incorrecto: 'En el Oeste no se da por vencido. ¡Otra vez!',
        nivel: 'Rango Vaquero',
        bienvenida: '¡Bienvenido al Viejo Oeste Matemático, forastero!',
      },
    },
  },
  {
    id: 'tema-princesas',
    nombre: 'Príncipes y Princesas Inventores',
    descripcion: 'Construye inventos, mide materiales y crea maravillas con el poder de los decimales.',
    categoria: 'tema',
    precio: 500,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '👑',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorPrimario: '#0891B2',
      colorSecundario: '#164E63',
      colorAccent: '#ECFEFF',
      efectoVictoria: 'invention-burst',
      vocabulario: {
        correcto: '¡Brillante ingenio, alteza!',
        incorrecto: 'Los grandes inventores aprenden del error. ¡Adelante!',
        nivel: 'Rango Real',
        bienvenida: '¡Bienvenido al Taller Real, alteza inventora!',
      },
    },
  },
];

// ============================================================
// FONDOS (3 por tema = 21 total, más 3 fondos genéricos)
// La nomenclatura: fondo-{temaId}-{1|2|3}
// Los fondos genéricos no pertenecen a ningún tema
// ============================================================
export const FONDOS: Desbloqueable[] = [
  // Fondos genéricos (disponibles para todos los temas)
  {
    id: 'fondo-cuadricula',
    nombre: 'Papel Cuadriculado',
    descripcion: 'Un fondo clásico de cuaderno matemático',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '📄',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { patron: 'patron', urlImagen: '/assets/fondos/papel-cuadriculado.png' },
  },
  {
    id: 'fondo-noche',
    nombre: 'Galaxia Infinita',
    descripcion: 'Un fondo espacial con números como galaxia',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌌',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { patron: 'gradiente', urlImagen: '/assets/fondos/galaxia.png' },
  },

  // ──────────────────────────────────────────────────────────────
  // Fondos temáticos
  // Cada tema tiene 3 fondos con tipo semántico fijo:
  //   fondoIndex 1 → ilustración  (escena realista o ilustración detallada)
  //   fondoIndex 2 → dibujo       (arte tipo libro ilustrado / cartoon)
  //   fondoIndex 3 → estampado    (patrón o motivo repetido del tema)
  // ──────────────────────────────────────────────────────────────

  // Fondos Piratas
  {
    id: 'fondo-piratas-1',
    nombre: 'Puerto Pirata',
    descripcion: 'El bullicioso puerto donde anclan los barcos corsarios',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '⚓',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-piratas', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/pirates/background_1.png' },
  },
  {
    id: 'fondo-piratas-2',
    nombre: 'Alta Mar',
    descripcion: 'El océano abierto con olas y horizonte infinito',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌊',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-piratas', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/pirates/background_2.png' },
  },
  {
    id: 'fondo-piratas-3',
    nombre: 'Estampado Pirata',
    descripcion: 'Calaveras, anclas y sables en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '💀',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-piratas', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/pirates/background_3.png' },
  },

  // Fondos Astronautas
  {
    id: 'fondo-astronautas-1',
    nombre: 'Estación Orbital',
    descripcion: 'La base espacial flotando sobre la Tierra',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🛸',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-astronautas', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/astronauts/background_1.png' },
  },
  {
    id: 'fondo-astronautas-2',
    nombre: 'Superficie Lunar',
    descripcion: 'El suelo gris de la Luna con la Tierra al fondo',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌕',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-astronautas', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/astronauts/background_2.png' },
  },
  {
    id: 'fondo-astronautas-3',
    nombre: 'Estampado Espacial',
    descripcion: 'Cohetes, planetas y estrellas en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🚀',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-astronautas', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/astronauts/background_3.png' },
  },

  // Fondos Magos
  {
    id: 'fondo-magos-1',
    nombre: 'Torre del Hechicero',
    descripcion: 'La antigua torre donde se dominan los números arcanos',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🏰',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-magos', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/wizards/background_1.png' },
  },
  {
    id: 'fondo-magos-2',
    nombre: 'Biblioteca Arcana',
    descripcion: 'Estantes repletos de libros de hechizos matemáticos',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '📚',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-magos', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/wizards/background_2.png' },
  },
  {
    id: 'fondo-magos-3',
    nombre: 'Estampado Mágico',
    descripcion: 'Estrellas, pociones y varitas en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '⭐',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-magos', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/wizards/background_3.png' },
  },

  // Fondos Caballeros
  {
    id: 'fondo-caballeros-1',
    nombre: 'Salón del Trono',
    descripcion: 'El gran salón donde se entregan los honores matemáticos',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '👑',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-caballeros', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/knights/background_1.png' },
  },
  {
    id: 'fondo-caballeros-2',
    nombre: 'Campo de Batalla',
    descripcion: 'Las llanuras donde los caballeros demuestran su valor',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '⚔️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-caballeros', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/knights/background_2.png' },
  },
  {
    id: 'fondo-caballeros-3',
    nombre: 'Estampado Medieval',
    descripcion: 'Escudos, espadas y coronas en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🛡️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-caballeros', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/knights/background_3.png' },
  },

  // Fondos Vaqueros
  {
    id: 'fondo-vaqueros-1',
    nombre: 'Pueblo del Oeste',
    descripcion: 'Las calles de tierra del pueblo donde hacen negocios los vaqueros',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🏚️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-vaqueros', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/cowboys/background_1.png' },
  },
  {
    id: 'fondo-vaqueros-2',
    nombre: 'Pradera al Atardecer',
    descripcion: 'Vastos campos dorados bajo el sol poniente',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🌅',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-vaqueros', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/cowboys/background_2.png' },
  },
  {
    id: 'fondo-vaqueros-3',
    nombre: 'Estampado Vaquero',
    descripcion: 'Botas, sombreros y herrajes en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🤠',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-vaqueros', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/cowboys/background_3.png' },
  },

  // Fondos Inventores
  {
    id: 'fondo-princesas-1',
    nombre: 'Taller Real',
    descripcion: 'El taller lleno de planos, engranajes e inventos a medio construir',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '⚙️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-princesas', fondoIndex: 1, fondoTipo: 'ilustracion', urlImagen: '/assets/themes/inventors/background_1.png' },
  },
  {
    id: 'fondo-princesas-2',
    nombre: 'Jardín del Palacio',
    descripcion: 'Los jardines geométricos donde se prueban los inventos',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '🌿',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-princesas', fondoIndex: 2, fondoTipo: 'dibujo', urlImagen: '/assets/themes/inventors/background_2.png' },
  },
  {
    id: 'fondo-princesas-3',
    nombre: 'Estampado Inventor',
    descripcion: 'Engranajes, bombillas y planos en patrón repetido',
    categoria: 'fondo',
    precio: 75,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '💡',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId: 'tema-princesas', fondoIndex: 3, fondoTipo: 'estampado', urlImagen: '/assets/themes/inventors/background_3.png' },
  },
];

// ============================================================
// COLORES (12 total)
// IDs alineados con archivo_referencia del seed de la BD
// ============================================================
export const COLORES: Desbloqueable[] = [
  // Colores básicos (Nivel 1, 50 pts)
  {
    id: 'color-azul-clasico',
    nombre: 'Azul Océano',
    descripcion: 'Un azul profundo y relajante',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '🔵',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#3B82F6', aplicaA: 'interfaz' },
  },
  {
    id: 'color-verde-esmeralda',
    nombre: 'Verde Bosque',
    descripcion: 'Natural y reconfortante',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '🟢',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#10B981', aplicaA: 'interfaz' },
  },
  {
    id: 'color-rojo-carmesi',
    nombre: 'Rojo Energía',
    descripcion: 'Lleno de energía y pasión',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '🔴',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#EF4444', aplicaA: 'interfaz' },
  },
  {
    id: 'color-naranja-solar',
    nombre: 'Naranja Solar',
    descripcion: 'Cálido y brillante como el sol',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '🟠',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#F97316', aplicaA: 'interfaz' },
  },
  {
    id: 'color-violeta-mistico',
    nombre: 'Morado Místico',
    descripcion: 'Misterioso y mágico',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '🟣',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#8B5CF6', aplicaA: 'interfaz' },
  },
  {
    id: 'color-turquesa',
    nombre: 'Turquesa Caribeño',
    descripcion: 'Como las aguas tropicales',
    categoria: 'color',
    precio: 50,
    nivelRequerido: 1,
    rareza: 'comun',
    icono: '💎',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#14B8A6', aplicaA: 'interfaz' },
  },
  // Colores premium (Nivel 2, 100 pts)
  {
    id: 'color-dorado-real',
    nombre: 'Oro Dorado',
    descripcion: 'Precioso y brillante',
    categoria: 'color',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '⭐',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#FBBF24', aplicaA: 'ambos' },
  },
  {
    id: 'color-rosa-sakura',
    nombre: 'Rosa Dulce',
    descripcion: 'Suave y encantador',
    categoria: 'color',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌸',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#EC4899', aplicaA: 'ambos' },
  },
  {
    id: 'color-azul-medianoche',
    nombre: 'Índigo Nocturno',
    descripcion: 'Profundo como la noche',
    categoria: 'color',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌙',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#6366F1', aplicaA: 'ambos' },
  },
  {
    id: 'color-verde-lima',
    nombre: 'Lima Fresca',
    descripcion: 'Refrescante y vivaz',
    categoria: 'color',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🍋',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#84CC16', aplicaA: 'ambos' },
  },
  {
    id: 'color-marron-cobre',
    nombre: 'Cobre Dorado',
    descripcion: 'Cálido tono cobrizo con estilo retro',
    categoria: 'color',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🟤',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { colorHex: '#B45309', aplicaA: 'ambos' },
  },
  // Color legendario (Nivel 3, 150 pts)
  {
    id: 'color-arcoiris',
    nombre: 'Arcoíris Mágico',
    descripcion: 'Todos los colores en uno (gradiente)',
    categoria: 'color',
    precio: 150,
    nivelRequerido: 3,
    rareza: 'legendario',
    icono: '🌈',
    estaDesbloqueado: false,
    esGratuito: false,
    config: {
      colorHex: 'linear-gradient(90deg, #FF0000, #FF7F00, #FFFF00, #00FF00, #0000FF, #4B0082, #9400D3)',
      aplicaA: 'ambos',
    },
  },
];

// ============================================================
// MÚSICAS (3 por tema = 18 total, más tema-default sin música)
// Los 3 tipos son FIJOS y se portan entre temas por índice:
//   musicaIndex 1 → tranquila   (melodía suave, para concentración)
//   musicaIndex 2 → energetica  (ritmo rápido, para motivarse)
//   musicaIndex 3 → ambiente    (sonidos del entorno del tema)
// La nomenclatura: musica-{temaId}-{tranquila|energetica|ambiente}
// ============================================================
export const MUSICAS: Desbloqueable[] = [
  // Músicas Piratas
  {
    id: 'musica-piratas-tranquila',
    nombre: 'Calma del Océano',
    descripcion: 'El suave vaivén de las olas para concentrarse',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌊',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-piratas', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/pirates/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-piratas-energetica',
    nombre: 'A la Carga, Marineros',
    descripcion: 'Acordeones y tambores de guerra en alta mar',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🏴‍☠️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-piratas', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/pirates/music_2_energetica.mp3' },
  },
  {
    id: 'musica-piratas-ambiente',
    nombre: 'Sonidos del Mar',
    descripcion: 'Gaviotas, olas y crujir del barco en alta mar',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '⚓',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-piratas', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/pirates/music_3_ambiente.mp3' },
  },

  // Músicas Astronautas
  {
    id: 'musica-astronautas-tranquila',
    nombre: 'Deriva Cósmica',
    descripcion: 'Sintetizadores suaves flotando en el silencio del espacio',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🌌',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-astronautas', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/astronauts/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-astronautas-energetica',
    nombre: 'Pulso Orbital',
    descripcion: 'Beats electrónicos de alta energía para los desafíos',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '🚀',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-astronautas', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/astronauts/music_2_energetica.mp3' },
  },
  {
    id: 'musica-astronautas-ambiente',
    nombre: 'Ecos del Cosmos',
    descripcion: 'Señales de radio, viento solar y zumbido de la nave',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'raro',
    icono: '⭐',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-astronautas', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/astronauts/music_3_ambiente.mp3' },
  },

  // Músicas Magos
  {
    id: 'musica-magos-tranquila',
    nombre: 'Meditación del Mago',
    descripcion: 'Suave melodía de laúd para estudiar los antiguos textos',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '📖',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-magos', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/wizards/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-magos-energetica',
    nombre: 'Duelo de Hechiceros',
    descripcion: 'Ritmo acelerado de percusión para los conjuros difíciles',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '✨',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-magos', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/wizards/music_2_energetica.mp3' },
  },
  {
    id: 'musica-magos-ambiente',
    nombre: 'El Taller Encantado',
    descripcion: 'Calderos burbujeando, truenos lejanos y crujir de libros viejos',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🧙',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-magos', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/wizards/music_3_ambiente.mp3' },
  },

  // Músicas Caballeros
  {
    id: 'musica-caballeros-tranquila',
    nombre: 'Vigilia del Caballero',
    descripcion: 'Suave melodía de laúd para la contemplación nocturna',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🌙',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-caballeros', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/knights/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-caballeros-energetica',
    nombre: 'Carga de Caballería',
    descripcion: 'Tambores y trompetas de guerra para las batallas difíciles',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '⚔️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-caballeros', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/knights/music_2_energetica.mp3' },
  },
  {
    id: 'musica-caballeros-ambiente',
    nombre: 'El Castillo Medieval',
    descripcion: 'Viento entre almenas, cuervos y el eco del gran salón',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🏰',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-caballeros', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/knights/music_3_ambiente.mp3' },
  },

  // Músicas Vaqueros
  {
    id: 'musica-vaqueros-tranquila',
    nombre: 'Viento del Desierto',
    descripcion: 'Guitarra suave y brisa cálida para los cálculos del comercio',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🌵',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-vaqueros', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/cowboys/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-vaqueros-energetica',
    nombre: 'Duelo al Mediodía',
    descripcion: 'Guitarra y armónica a ritmo tenso para los problemas difíciles',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '☀️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-vaqueros', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/cowboys/music_2_energetica.mp3' },
  },
  {
    id: 'musica-vaqueros-ambiente',
    nombre: 'La Pradera Viva',
    descripcion: 'Grillos, brisa, hoguera y lejano mugido de ganado',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'epico',
    icono: '🤠',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-vaqueros', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/cowboys/music_3_ambiente.mp3' },
  },

  // Músicas Princesas Inventoras
  {
    id: 'musica-princesas-tranquila',
    nombre: 'Engranajes en Movimiento',
    descripcion: 'Melodía mecánica y suave para diseñar en el taller',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '⚙️',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-princesas', musicaIndex: 1, musicaTipo: 'tranquila', tipo: 'concentracion', duracion: 240, urlAudio: '/assets/themes/inventors/music_1_tranquila.mp3' },
  },
  {
    id: 'musica-princesas-energetica',
    nombre: 'Máquina a Plena Marcha',
    descripcion: 'Ritmo industrial acelerado para los inventos más complejos',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '🔧',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-princesas', musicaIndex: 2, musicaTipo: 'energetica', tipo: 'energica', duracion: 180, urlAudio: '/assets/themes/inventors/music_2_energetica.mp3' },
  },
  {
    id: 'musica-princesas-ambiente',
    nombre: 'El Taller Real',
    descripcion: 'Herramientas, vapor, tic-tac de relojes y el bullicio del taller',
    categoria: 'musica',
    precio: 100,
    nivelRequerido: 2,
    rareza: 'legendario',
    icono: '👑',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { temaId_musica: 'tema-princesas', musicaIndex: 3, musicaTipo: 'ambiente', tipo: 'aventura', duracion: 200, urlAudio: '/assets/themes/inventors/music_3_ambiente.mp3' },
  },
];


// ============================================================
// EFECTOS ESPECIALES (5 total)
// ============================================================
export const EFECTOS: Desbloqueable[] = [
  {
    id: 'efecto-estrellas',
    nombre: 'Lluvia de Estrellas',
    descripcion: 'Estrellas brillantes caen al resolver correctamente',
    categoria: 'efecto',
    precio: 100,
    nivelRequerido: 3,
    rareza: 'raro',
    icono: '✨',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { animacion: 'stars-fall', duracionMs: 2000, sonido: '/assets/sound_effects/estrellas.mp3' },
  },
  {
    id: 'efecto-confeti',
    nombre: 'Explosión de Confeti',
    descripcion: 'Celebra con una explosión de colores',
    categoria: 'efecto',
    precio: 100,
    nivelRequerido: 3,
    rareza: 'raro',
    icono: '🎉',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { animacion: 'confetti-burst', duracionMs: 1500, sonido: '/assets/sound_effects/confetti.mp3' },
  },
  {
    id: 'efecto-fuegos',
    nombre: 'Fuegos Artificiales',
    descripcion: 'Espectáculo pirotécnico por tu éxito',
    categoria: 'efecto',
    precio: 150,
    nivelRequerido: 4,
    rareza: 'epico',
    icono: '🎆',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { animacion: 'fireworks', duracionMs: 3000, sonido: '/assets/sound_effects/fuegos_artificiales.mp3' },
  },
  {
    id: 'efecto-rayo',
    nombre: 'Poder del Rayo',
    descripcion: 'Un rayo eléctrico atraviesa la pantalla',
    categoria: 'efecto',
    precio: 150,
    nivelRequerido: 4,
    rareza: 'epico',
    icono: '⚡',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { animacion: 'lightning-strike', duracionMs: 1000, sonido: '/assets/sound_effects/rayos.mp3' },
  },
  {
    id: 'efecto-aurora',
    nombre: 'Aurora Boreal',
    descripcion: 'Luces del norte danzan en la pantalla',
    categoria: 'efecto',
    precio: 150,
    nivelRequerido: 5,
    rareza: 'legendario',
    icono: '🌌',
    estaDesbloqueado: false,
    esGratuito: false,
    config: { animacion: 'aurora-borealis', duracionMs: 4000, sonido: '/assets/sound_effects/boreal.mp3' },
  },
];

// ============================================================
// HELPERS
// ============================================================

export function getTodosLosDesbloqueables(): Desbloqueable[] {
  return [...TEMAS, ...FONDOS, ...COLORES, ...MUSICAS, ...EFECTOS];
}

export function getDesbloqueablesPorCategoria(categoria: CategoriaDesbloqueable): Desbloqueable[] {
  switch (categoria) {
    case 'tema':    return TEMAS;
    case 'fondo':   return FONDOS;
    case 'color':   return COLORES;
    case 'musica':  return MUSICAS;
    case 'efecto':  return EFECTOS;
    default:        return [];
  }
}

export function getDesbloquablesDisponibles(nivelEstudiante: number): Desbloqueable[] {
  return getTodosLosDesbloqueables().filter(item => item.nivelRequerido <= nivelEstudiante);
}

/** Devuelve los fondos que pertenecen a un tema específico (fondoIndex 1, 2, 3) */
export function getFondosPorTema(temaId: string): Desbloqueable[] {
  return FONDOS.filter(f => f.config?.temaId === temaId).sort(
    (a, b) => (a.config?.fondoIndex ?? 0) - (b.config?.fondoIndex ?? 0)
  );
}

/** Devuelve las músicas que pertenecen a un tema específico (musicaIndex 1, 2, 3) */
export function getMusicasPorTema(temaId: string): Desbloqueable[] {
  return MUSICAS.filter(m => m.config?.temaId_musica === temaId).sort(
    (a, b) => (a.config?.musicaIndex ?? 0) - (b.config?.musicaIndex ?? 0)
  );
}
