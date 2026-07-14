import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useMultiplicationCalculator } from '@/hooks/useMultiplicationCalculator'

describe('useMultiplicationCalculator', () => {
  it('multiplicación entera básica: 6 × 7 = 42', () => {
    const { result } = renderHook(() => useMultiplicationCalculator(6, 7))
    expect(result.current.resultadoStr).toBe('42')
    expect(result.current.totalDecimales).toBe(0)
  })

  it('2.5 × 1.5 = 3.75 sin errores de punto flotante', () => {
    // En JS nativo, 25 × 15 = 375 y luego insertarDecimal lo convierte a "3.75"
    const { result } = renderHook(() => useMultiplicationCalculator(2.5, 1.5))
    expect(result.current.resultadoStr).toBe('3.75')
    expect(result.current.totalDecimales).toBe(2)
  })

  it('23 × 45: dos productos parciales con valores y posiciones correctas', () => {
    const { result } = renderHook(() => useMultiplicationCalculator(23, 45))
    const { productosParciales, resultadoStr } = result.current
    expect(resultadoStr).toBe('1035')
    expect(productosParciales).toHaveLength(2)
    expect(productosParciales[0].valor).toBe(115)  // 23 × 5 (unidades)
    expect(productosParciales[0].espacios).toBe(0)
    expect(productosParciales[1].valor).toBe(92)   // 23 × 4 (decenas, desplazado)
    expect(productosParciales[1].espacios).toBe(1)
  })

  it('multiplicar por 1 devuelve el mismo número', () => {
    const { result } = renderHook(() => useMultiplicationCalculator(42, 1))
    expect(result.current.resultadoStr).toBe('42')
  })

  it('multiplicar por 0 da resultado "0"', () => {
    const { result } = renderHook(() => useMultiplicationCalculator(15, 0))
    expect(result.current.resultadoStr).toBe('0')
  })
})
