import { describe, it, expect } from 'vitest'
import { generarPasos } from '@/utils/generarPasos'

describe('generarPasos', () => {

  describe('SUMA', () => {
    it('genera al menos un paso', () => {
      const pasos = generarPasos('SUMA', 7, 5)
      expect(pasos.length).toBeGreaterThan(0)
    })

    it('el primer paso indica alinear los números', () => {
      const pasos = generarPasos('SUMA', 7, 5)
      expect(pasos[0].titulo.toLowerCase()).toContain('alinea')
    })

    it('el último paso contiene el resultado correcto (7+5=12)', () => {
      const pasos = generarPasos('SUMA', 7, 5)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('12')
      expect(ultimo.descripcion).toContain('✓')
    })

    it('suma con acarreo genera un paso de "llevado" o "extra"', () => {
      // 7+5=12 necesita llevar 1 a la columna de decenas
      const pasos = generarPasos('SUMA', 7, 5)
      const tieneAcarreo = pasos.some(
        p => p.titulo.toLowerCase().includes('llevado') || p.titulo.toLowerCase().includes('extra')
      )
      expect(tieneAcarreo).toBe(true)
    })

    it('suma con decimales: resultado final es correcto (1.5+2.5=4)', () => {
      const pasos = generarPasos('SUMA', 1.5, 2.5)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('4')
    })

    it('suma sin acarreo (2+3=5) no genera paso de acarreo', () => {
      const pasos = generarPasos('SUMA', 2, 3)
      const tieneAcarreo = pasos.some(
        p => p.titulo.toLowerCase().includes('llevado') || p.titulo.toLowerCase().includes('extra')
      )
      expect(tieneAcarreo).toBe(false)
    })
  })

  describe('RESTA', () => {
    it('el último paso contiene el resultado correcto (20-7=13)', () => {
      const pasos = generarPasos('RESTA', 20, 7)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('13')
    })

    it('resta con préstamo incluye descripción de "prestado"', () => {
      // Columna de unidades: 0 < 7, necesita pedir prestado
      const pasos = generarPasos('RESTA', 20, 7)
      const tienePrestamo = pasos.some(p => p.descripcion.includes('prestado'))
      expect(tienePrestamo).toBe(true)
    })

    it('resta sin préstamo (9-4=5) no menciona préstamo', () => {
      const pasos = generarPasos('RESTA', 9, 4)
      const tienePrestamo = pasos.some(p => p.descripcion.includes('prestado'))
      expect(tienePrestamo).toBe(false)
    })
  })

  describe('MULTIPLICACION', () => {
    it('el último paso contiene el resultado correcto (6×4=24)', () => {
      const pasos = generarPasos('MULTIPLICACION', 6, 4)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('24')
    })

    it('multiplicación con decimales: 2.5 × 1.5 = 3.75', () => {
      const pasos = generarPasos('MULTIPLICACION', 2.5, 1.5)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('3.75')
    })

    it('incluye paso de "Cuenta los decimales"', () => {
      const pasos = generarPasos('MULTIPLICACION', 2.5, 1.5)
      const tieneDecimales = pasos.some(p => p.titulo.toLowerCase().includes('decimal'))
      expect(tieneDecimales).toBe(true)
    })
  })

  describe('DIVISION', () => {
    it('el último paso contiene el resultado correcto (12÷3=4)', () => {
      const pasos = generarPasos('DIVISION', 12, 3, 1)
      const ultimo = pasos[pasos.length - 1]
      expect(ultimo.titulo).toContain('4')
      expect(ultimo.descripcion).toContain('✓')
    })

    it('los pasos intermedios tienen el formato "X ÷ divisor = Q"', () => {
      const pasos = generarPasos('DIVISION', 12, 3, 1)
      const tieneFormato = pasos.some(p => p.titulo.includes('÷'))
      expect(tieneFormato).toBe(true)
    })

    it('el primer paso indica plantear la división', () => {
      const pasos = generarPasos('DIVISION', 12, 3, 1)
      expect(pasos[0].titulo.toLowerCase()).toContain('plantea')
    })
  })

  it('operación desconocida devuelve array vacío', () => {
    // @ts-expect-error — probando entrada inválida intencionalmente
    const pasos = generarPasos('MODULO', 10, 3)
    expect(pasos).toEqual([])
  })
})
