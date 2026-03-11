/**
 * Store de personalización / tema activo (Sección 4.4.6)
 *
 * Lógica de portabilidad de fondo y música:
 *   Cuando el estudiante cambia de tema, el fondo activo y la música
 *   activa se mantienen por su ÍNDICE (1, 2 o 3) dentro del nuevo tema.
 *   Ejemplo: estaba en piratas con fondo-2 → pasa a astronautas → se activa
 *   fondo-astronautas-2 automáticamente.
 *
 *   Los fondos/músicas genéricos (sin temaId) no cambian al cambiar de tema.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  TEMAS,
  FONDOS,
  MUSICAS,
  COLORES,
  getFondosPorTema,
  getMusicasPorTema,
  type Desbloqueable,
} from '@/types/shop';

// ----------------------------------------------------------------
// Tipos
// ----------------------------------------------------------------

export interface PreferenciasTema {
  /** Id del fondo activo dentro de ese tema (null = sin fondo) */
  fondoActivoId: string | null;
  /** Índice (1-3) del fondo activo, para portabilidad */
  fondoActivoIndex: number | null;
  /** Id de la música activa dentro de ese tema (null = sin música) */
  musicaActivaId: string | null;
  /** Índice (1-3) de la música activa, para portabilidad */
  musicaActivaIndex: number | null;
}

interface ThemeState {
  // ---- Selecciones activas ----
  temaActivoId: string;
  colorActivoId: string | null;
  efectoActivoId: string | null;

  // ---- Audio ----
  audioActivado: boolean;
  volumen: number; // 0-100
  efectosSonidoActivados: boolean; // clicks, correcto/incorrecto, efectos victoria

  // ---- Notificaciones ----
  notificacionesActivadas: boolean;
  notifDesafios: boolean;
  notifLogros: boolean;
  notifRecordatorios: boolean;

  /**
   * Preferencias de fondo y música por temaId.
   * Se guardan por separado para que al volver a un tema
   * se restauren las últimas preferencias del estudiante.
   */
  preferenciasPorTema: Record<string, PreferenciasTema>;

  // ---- Acciones ----
  setTemaActivo: (temaId: string) => void;
  setFondoActivo: (fondoId: string | null) => void;
  setMusicaActiva: (musicaId: string | null) => void;
  setColorActivo: (colorId: string | null) => void;
  setEfectoActivo: (efectoId: string | null) => void;
  setAudioActivado: (activado: boolean) => void;
  setVolumen: (vol: number) => void;
  setEfectosSonidoActivados: (v: boolean) => void;
  setNotificacionesActivadas: (activado: boolean) => void;
  setNotifDesafios: (v: boolean) => void;
  setNotifLogros: (v: boolean) => void;
  setNotifRecordatorios: (v: boolean) => void;

  // ---- Helpers de lectura ----
  getTemaActivo: () => Desbloqueable | undefined;
  getFondoActivo: () => Desbloqueable | null;
  getMusicaActiva: () => Desbloqueable | null;
  getColorActivo: () => Desbloqueable | null;
}

// ----------------------------------------------------------------
// Helpers internos
// ----------------------------------------------------------------

function getPreferenciaDefault(): PreferenciasTema {
  return {
    fondoActivoId: null,
    fondoActivoIndex: null,
    musicaActivaId: null,
    musicaActivaIndex: null,
  };
}

/**
 * Dado un temaId y un índice (1-3), devuelve el id del fondo
 * correspondiente a ese tema e índice. Devuelve null si no existe.
 */
function resolverFondoPorIndice(temaId: string, index: number | null): string | null {
  if (!index) return null;
  const fondos = getFondosPorTema(temaId);
  const fondo = fondos.find(f => f.config?.fondoIndex === index);
  return fondo?.id ?? null;
}

/**
 * Dado un temaId y un índice (1-3), devuelve el id de la música
 * correspondiente a ese tema e índice. Devuelve null si no existe.
 */
function resolverMusicaPorIndice(temaId: string, index: number | null): string | null {
  if (!index) return null;
  const musicas = getMusicasPorTema(temaId);
  const musica = musicas.find(m => m.config?.musicaIndex === index);
  return musica?.id ?? null;
}

// ----------------------------------------------------------------
// Store
// ----------------------------------------------------------------

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // Estado inicial
      temaActivoId: 'tema-default',
      colorActivoId: null,
      efectoActivoId: null,
      audioActivado: false,
      volumen: 70,
      efectosSonidoActivados: true,
      notificacionesActivadas: true,
      notifDesafios: true,
      notifLogros: true,
      notifRecordatorios: true,
      preferenciasPorTema: {
        'tema-default': getPreferenciaDefault(),
      },

      // ---- Cambiar tema ----
      setTemaActivo: (temaId: string) => {
        set(state => {
          const prevTemaId = state.temaActivoId;
          const prevPrefs = state.preferenciasPorTema[prevTemaId] ?? getPreferenciaDefault();

          // Recuperar o crear preferencias del nuevo tema
          const existingPrefs = state.preferenciasPorTema[temaId];

          let newPrefs: PreferenciasTema;

          if (existingPrefs) {
            // El estudiante ya estuvo en este tema: restaurar sus preferencias
            newPrefs = existingPrefs;
          } else {
            // Primera vez en este tema: portar por índice desde el tema anterior
            const prevFondoIndex = prevPrefs.fondoActivoIndex;
            const prevMusicaIndex = prevPrefs.musicaActivaIndex;

            const nuevoFondoId = resolverFondoPorIndice(temaId, prevFondoIndex);
            const nuevaMusicaId = resolverMusicaPorIndice(temaId, prevMusicaIndex ?? null);

            // Obtener el índice del fondo/música resuelto
            const nuevoFondo = FONDOS.find(f => f.id === nuevoFondoId);
            const nuevaMusica = MUSICAS.find(m => m.id === nuevaMusicaId);

            newPrefs = {
              fondoActivoId: nuevoFondoId,
              fondoActivoIndex: nuevoFondo?.config?.fondoIndex ?? null,
              musicaActivaId: nuevaMusicaId,
              musicaActivaIndex: nuevaMusica?.config?.musicaIndex ?? null,
            };
          }

          return {
            temaActivoId: temaId,
            preferenciasPorTema: {
              ...state.preferenciasPorTema,
              // Guardar preferencias del tema anterior antes de salir
              [prevTemaId]: prevPrefs,
              // Cargar preferencias del nuevo tema
              [temaId]: newPrefs,
            },
          };
        });
      },

      // ---- Cambiar fondo (dentro del tema activo) ----
      setFondoActivo: (fondoId: string | null) => {
        set(state => {
          const temaId = state.temaActivoId;
          const fondo = fondoId ? FONDOS.find(f => f.id === fondoId) : null;
          const fondoIndex = fondo?.config?.fondoIndex ?? null;

          return {
            preferenciasPorTema: {
              ...state.preferenciasPorTema,
              [temaId]: {
                ...(state.preferenciasPorTema[temaId] ?? getPreferenciaDefault()),
                fondoActivoId: fondoId,
                fondoActivoIndex: fondoIndex,
              },
            },
          };
        });
      },

      // ---- Cambiar música (dentro del tema activo) ----
      setMusicaActiva: (musicaId: string | null) => {
        set(state => {
          const temaId = state.temaActivoId;
          const musica = musicaId ? MUSICAS.find(m => m.id === musicaId) : null;
          const musicaIndex = musica?.config?.musicaIndex ?? null;

          return {
            preferenciasPorTema: {
              ...state.preferenciasPorTema,
              [temaId]: {
                ...(state.preferenciasPorTema[temaId] ?? getPreferenciaDefault()),
                musicaActivaId: musicaId,
                musicaActivaIndex: musicaIndex,
              },
            },
          };
        });
      },

      // ---- Cambiar color ----
      setColorActivo: (colorId: string | null) => set({ colorActivoId: colorId }),

      // ---- Cambiar efecto ----
      setEfectoActivo: (efectoId: string | null) => set({ efectoActivoId: efectoId }),

      // ---- Audio ----
      setAudioActivado: (activado: boolean) => set({ audioActivado: activado }),
      setVolumen: (vol: number) => set({ volumen: Math.min(100, Math.max(0, vol)) }),
      setEfectosSonidoActivados: (v: boolean) => set({ efectosSonidoActivados: v }),

      // ---- Notificaciones ----
      setNotificacionesActivadas: (activado: boolean) =>
        set({ notificacionesActivadas: activado }),
      setNotifDesafios: (v: boolean) => set({ notifDesafios: v }),
      setNotifLogros: (v: boolean) => set({ notifLogros: v }),
      setNotifRecordatorios: (v: boolean) => set({ notifRecordatorios: v }),

      // ---- Helpers de lectura ----
      getTemaActivo: () => {
        const { temaActivoId } = get();
        return TEMAS.find(t => t.id === temaActivoId);
      },

      getFondoActivo: () => {
        const { temaActivoId, preferenciasPorTema } = get();
        const prefs = preferenciasPorTema[temaActivoId];
        if (!prefs?.fondoActivoId) return null;
        return FONDOS.find(f => f.id === prefs.fondoActivoId) ?? null;
      },

      getMusicaActiva: () => {
        const { temaActivoId, preferenciasPorTema } = get();
        const prefs = preferenciasPorTema[temaActivoId];
        if (!prefs?.musicaActivaId) return null;
        return MUSICAS.find(m => m.id === prefs.musicaActivaId) ?? null;
      },

      getColorActivo: () => {
        const { colorActivoId } = get();
        if (!colorActivoId) return null;
        return COLORES.find(c => c.id === colorActivoId) ?? null;
      },
    }),
    {
      name: 'sti-theme-preferences', // clave en localStorage
    }
  )
);
