import { beforeEach, describe, it, expect } from 'vitest'
import { useThemeStore } from '@/store/themeStore'

const ESTADO_INICIAL = {
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
    'tema-default': {
      fondoActivoId: null,
      fondoActivoIndex: null,
      musicaActivaId: null,
      musicaActivaIndex: null,
    },
  },
}

beforeEach(() => {
  // Limpia localStorage para evitar que persist rehidrate estado de una prueba anterior
  localStorage.clear()
  // Merge sin replace=true: resetea los datos pero conserva las funciones del store
  useThemeStore.setState(ESTADO_INICIAL)
})

describe('useThemeStore', () => {
  it('estado inicial: tema activo es "tema-default"', () => {
    expect(useThemeStore.getState().temaActivoId).toBe('tema-default')
  })

  it('setTemaActivo cambia el temaActivoId', () => {
    useThemeStore.getState().setTemaActivo('tema-piratas')
    expect(useThemeStore.getState().temaActivoId).toBe('tema-piratas')
  })

  it('setFondoActivo actualiza el fondoActivoId del tema activo', () => {
    useThemeStore.getState().setFondoActivo('fondo-abc')
    const prefs = useThemeStore.getState().preferenciasPorTema['tema-default']
    expect(prefs.fondoActivoId).toBe('fondo-abc')
  })

  it('setMusicaActiva actualiza la musicaActivaId del tema activo', () => {
    useThemeStore.getState().setMusicaActiva('musica-xyz')
    const prefs = useThemeStore.getState().preferenciasPorTema['tema-default']
    expect(prefs.musicaActivaId).toBe('musica-xyz')
  })

  it('las preferencias de cada tema son independientes', () => {
    const { setTemaActivo, setFondoActivo } = useThemeStore.getState()

    // Activar un fondo en tema-default (ID ficticio → fondoIndex=null)
    setFondoActivo('fondo-test-1')
    expect(useThemeStore.getState().preferenciasPorTema['tema-default'].fondoActivoId).toBe('fondo-test-1')

    // Cambiar a otro tema
    setTemaActivo('tema-otro')

    // El nuevo tema no debe heredar el fondoActivoId del anterior
    // (el portado por índice no aplica porque fondoActivoIndex=null)
    const prefsOtro = useThemeStore.getState().preferenciasPorTema['tema-otro']
    expect(prefsOtro).toBeDefined()
    expect(prefsOtro?.fondoActivoId).not.toBe('fondo-test-1')
  })

  it('al volver a un tema anterior se restauran sus preferencias originales', () => {
    const { setTemaActivo, setFondoActivo } = useThemeStore.getState()

    // Guardar preferencia en tema-default
    setFondoActivo('fondo-preferido')

    // Ir a otro tema (esto guarda las preferencias de tema-default)
    setTemaActivo('tema-otro')

    // Volver a tema-default
    setTemaActivo('tema-default')

    // Las preferencias deben restaurarse exactamente
    const prefs = useThemeStore.getState().preferenciasPorTema['tema-default']
    expect(prefs.fondoActivoId).toBe('fondo-preferido')
  })
})
