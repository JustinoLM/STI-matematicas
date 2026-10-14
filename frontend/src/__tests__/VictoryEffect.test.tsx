import { StrictMode } from 'react'
import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const playSound = vi.fn()
vi.mock('@/utils', () => ({ playSound: (...args: unknown[]) => playSound(...args) }))

import { VictoryEffect } from '@/components/practice/VictoryEffect'

// jsdom no implementa canvas: se simula un contexto vacío para que el efecto se ejecute
function contextoFalso() {
  return new Proxy({}, { get: () => () => ({ addColorStop: () => undefined }), set: () => true })
}

describe('VictoryEffect', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    playSound.mockClear()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(contextoFalso() as never)
    vi.stubGlobal('requestAnimationFrame', () => 1)
    vi.stubGlobal('cancelAnimationFrame', () => undefined)
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('suena una sola vez aunque React ejecute el efecto dos veces (StrictMode)', () => {
    render(
      <StrictMode>
        <VictoryEffect animacion="stars-fall" duracionMs={100} sonido="/s.mp3" audioVolumen={50} onDone={() => undefined} />
      </StrictMode>
    )
    expect(playSound).toHaveBeenCalledTimes(1)
  })

  it('un re-render del padre con otra función onDone no repite el sonido ni la animación', () => {
    const onDone = vi.fn()
    const { rerender } = render(
      <VictoryEffect animacion="confetti-burst" duracionMs={100} sonido="/s.mp3" audioVolumen={50} onDone={onDone} />
    )
    rerender(
      <VictoryEffect animacion="confetti-burst" duracionMs={100} sonido="/s.mp3" audioVolumen={50} onDone={() => onDone()} />
    )
    expect(playSound).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(200)
    expect(onDone).toHaveBeenCalledTimes(1)   // termina una sola vez
  })

  it('otra respuesta correcta (otra key) reproduce el efecto de nuevo, una vez', () => {
    const { rerender } = render(
      <VictoryEffect key={1} animacion="stars-fall" duracionMs={100} sonido="/s.mp3" audioVolumen={50} onDone={() => undefined} />
    )
    rerender(
      <VictoryEffect key={2} animacion="stars-fall" duracionMs={100} sonido="/s.mp3" audioVolumen={50} onDone={() => undefined} />
    )
    expect(playSound).toHaveBeenCalledTimes(2)
  })
})
