import { describe, it, expect } from 'vitest'
import { validarRespuesta, respuestaEsCorrecta } from '@/utils/validacionRespuestas'

describe('regla de corrección: redondeo a 3 decimales (mitad hacia arriba)', () => {
  it('12.34 frente a 12.35 es incorrecta', () => {
    expect(respuestaEsCorrecta('12.34', 12.35)).toBe(false)
    expect(validarRespuesta('SUMA', '12.34', 10, 2.35, 12.35).esCorrecta).toBe(false)
  })

  it('20.8 frente a 20.80 es correcta (escritura equivalente)', () => {
    expect(respuestaEsCorrecta('20.8', 20.8)).toBe(true)
    expect(respuestaEsCorrecta('20.80', 20.8)).toBe(true)
    expect(respuestaEsCorrecta('20.8', 20.800)).toBe(true)
  })

  it('18.5175 frente a 18.518 es correcta (redondea 18.5175 → 18.518)', () => {
    expect(respuestaEsCorrecta('18.5175', 18.518)).toBe(true)
    expect(validarRespuesta('DIVISION', '18.5175', 74.07, 4, 18.518).esCorrecta).toBe(true)
  })

  it('18.5174 frente a 18.518 es incorrecta (redondea a 18.517)', () => {
    expect(respuestaEsCorrecta('18.5174', 18.518)).toBe(false)
  })

  it('no depende de la coma flotante binaria', () => {
    expect(respuestaEsCorrecta('1.0005', 1.001)).toBe(true)
    expect(respuestaEsCorrecta('2.675', 2.675)).toBe(true)
    expect(respuestaEsCorrecta('-1.0005', -1.001)).toBe(true)  // mitad hacia arriba en valor absoluto
  })

  it('texto que no es un número es incorrecto', () => {
    expect(respuestaEsCorrecta('abc', 5)).toBe(false)
    expect(respuestaEsCorrecta('', 5)).toBe(false)
    expect(respuestaEsCorrecta('.', 5)).toBe(false)
  })
})

describe('validarRespuesta', () => {

  describe('SUMA', () => {
    it('respuesta correcta exacta', () => {
      const r = validarRespuesta('SUMA', '8', 5, 3, 8)
      expect(r.esCorrecta).toBe(true)
      expect(r.resultadoCorrecto).toBe(true)
    })

    it('respuesta incorrecta', () => {
      const r = validarRespuesta('SUMA', '9', 5, 3, 8)
      expect(r.esCorrecta).toBe(false)
    })

    it('respuesta vacía', () => {
      const r = validarRespuesta('SUMA', '', 5, 3, 8)
      expect(r.esCorrecta).toBe(false)
    })

    it('respuesta solo espacios', () => {
      const r = validarRespuesta('SUMA', '   ', 5, 3, 8)
      expect(r.esCorrecta).toBe(false)
    })

    it('respuesta no numérica (texto)', () => {
      const r = validarRespuesta('SUMA', 'ocho', 5, 3, 8)
      expect(r.esCorrecta).toBe(false)
    })

    it('tolerancia de punto flotante: 0.1 + 0.2 es reconocido como 0.3', () => {
      // En JS nativo, 0.1 + 0.2 = 0.30000000000000004
      // El estudiante escribe "0.30" — debe ser aceptado
      const r = validarRespuesta('SUMA', '0.30', 0.1, 0.2, 0.3)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta con espacios al inicio y fin es aceptada', () => {
      const r = validarRespuesta('SUMA', '  8  ', 5, 3, 8)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta distinta del resultado al redondear a 3 decimales es rechazada', () => {
      // 8.02 redondeado a 3 decimales (8.020) no es igual a 8
      const r = validarRespuesta('SUMA', '8.02', 5, 3, 8)
      expect(r.esCorrecta).toBe(false)
    })
  })

  describe('RESTA', () => {
    it('respuesta correcta', () => {
      const r = validarRespuesta('RESTA', '7', 10, 3, 7)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta incorrecta', () => {
      const r = validarRespuesta('RESTA', '6', 10, 3, 7)
      expect(r.esCorrecta).toBe(false)
    })

    it('resultado decimal: 5.5 - 2.3 = 3.2', () => {
      const r = validarRespuesta('RESTA', '3.2', 5.5, 2.3, 3.2)
      expect(r.esCorrecta).toBe(true)
    })
  })

  describe('MULTIPLICACION', () => {
    it('respuesta correcta entera', () => {
      const r = validarRespuesta('MULTIPLICACION', '12', 4, 3, 12)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta incorrecta', () => {
      const r = validarRespuesta('MULTIPLICACION', '11', 4, 3, 12)
      expect(r.esCorrecta).toBe(false)
    })

    it('resultado decimal: 2.5 × 1.5 = 3.75', () => {
      const r = validarRespuesta('MULTIPLICACION', '3.75', 2.5, 1.5, 3.75)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta vacía es incorrecta', () => {
      const r = validarRespuesta('MULTIPLICACION', '', 4, 3, 12)
      expect(r.esCorrecta).toBe(false)
    })
  })

  describe('DIVISION', () => {
    it('división exacta', () => {
      const r = validarRespuesta('DIVISION', '4', 12, 3, 4)
      expect(r.esCorrecta).toBe(true)
    })

    it('resultado decimal: 5 ÷ 2 = 2.5', () => {
      const r = validarRespuesta('DIVISION', '2.5', 5, 2, 2.5)
      expect(r.esCorrecta).toBe(true)
    })

    it('respuesta incorrecta', () => {
      const r = validarRespuesta('DIVISION', '3', 12, 3, 4)
      expect(r.esCorrecta).toBe(false)
    })

    it('respuesta NaN (guión, texto) es incorrecta', () => {
      const r = validarRespuesta('DIVISION', '-', 12, 3, 4)
      expect(r.esCorrecta).toBe(false)
    })
  })

  it('operación desconocida devuelve esCorrecta=false', () => {
    // @ts-expect-error — probando entrada inválida intencionalmente
    const r = validarRespuesta('MODULO', '1', 10, 3, 1)
    expect(r.esCorrecta).toBe(false)
  })
})
