import { describe, it, expect } from 'vitest'
import {
  normalizarDecimales,
  alinearDecimales,
  calcularProductosParciales,
} from '@/utils/mathOperations'

describe('normalizarDecimales', () => {
  it('ambos enteros: factor=1, valores sin cambio', () => {
    const r = normalizarDecimales(10, 2)
    expect(r.dividendoN).toBe(10)
    expect(r.divisorN).toBe(2)
    expect(r.factor).toBe(1)
  })

  it('un decimal cada uno: 12.5 ÷ 2.5 → 125 ÷ 25', () => {
    const r = normalizarDecimales(12.5, 2.5)
    expect(r.dividendoN).toBe(125)
    expect(r.divisorN).toBe(25)
    expect(r.factor).toBe(10)
  })

  it('distinta precisión decimal: toma el máximo (3.75 ÷ 1.5 → ×100)', () => {
    const r = normalizarDecimales(3.75, 1.5)
    expect(r.dividendoN).toBe(375)
    expect(r.divisorN).toBe(150)
    expect(r.factor).toBe(100)
  })

  it('entero dividido decimal: 6 ÷ 1.5 → 60 ÷ 15', () => {
    const r = normalizarDecimales(6, 1.5)
    expect(r.dividendoN).toBe(60)
    expect(r.divisorN).toBe(15)
    expect(r.factor).toBe(10)
  })
})

describe('alinearDecimales', () => {
  it('ambos enteros: maxDecimales=0, sin punto decimal', () => {
    const r = alinearDecimales(10, 5)
    expect(r.maxDecimales).toBe(0)
    expect(r.maxEnteros).toBe(2)
  })

  it('distinta cantidad de decimales: rellena el más corto con ceros', () => {
    const r = alinearDecimales(500.75, 234.5)
    expect(r.num1Alineado).toBe('500.75')
    expect(r.num2Alineado).toBe('234.50')
    expect(r.maxDecimales).toBe(2)
  })

  it('misma cantidad de decimales: sin relleno', () => {
    const r = alinearDecimales(1.5, 2.5)
    expect(r.maxDecimales).toBe(1)
    expect(r.num1Alineado).toContain('1.5')
    expect(r.num2Alineado).toContain('2.5')
  })

  it('maxEnteros refleja la parte entera más larga', () => {
    const r = alinearDecimales(100, 5)
    expect(r.maxEnteros).toBe(3)
  })
})

describe('calcularProductosParciales', () => {
  it('multiplicador de un dígito: un único parcial', () => {
    const ps = calcularProductosParciales(23, 4)
    expect(ps).toHaveLength(1)
    expect(ps[0].valor).toBe(92)   // 23 × 4
    expect(ps[0].posicion).toBe(0)
  })

  it('multiplicador de dos dígitos: dos parciales con posición correcta', () => {
    const ps = calcularProductosParciales(12, 23)
    expect(ps).toHaveLength(2)
    expect(ps[0].valor).toBe(36)   // 12 × 3 (unidades)
    expect(ps[0].posicion).toBe(0)
    expect(ps[1].valor).toBe(24)   // 12 × 2 (decenas, desplazado)
    expect(ps[1].posicion).toBe(1)
  })

  it('multiplicar por cero: parcial con valor 0', () => {
    const ps = calcularProductosParciales(99, 0)
    expect(ps).toHaveLength(1)
    expect(ps[0].valor).toBe(0)
  })

  it('la suma de parciales desplazados da el producto total', () => {
    // 12 × 23 = 276
    // parciales: 36×10^0 + 24×10^1 = 36 + 240 = 276
    const ps = calcularProductosParciales(12, 23)
    const total = ps.reduce((sum, p) => sum + p.valor * Math.pow(10, p.posicion), 0)
    expect(total).toBe(276)
  })
})
