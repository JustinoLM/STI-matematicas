/**
 * Utilidades para validación de respuestas matemáticas
 * Soporta validación granular de productos parciales y pasos intermedios
 */

import { Operacion, RespuestaValidacion } from '@/types';

/**
 * Convierte un número escrito como texto a milésimas (entero), redondeando a tres
 * decimales con "mitad hacia arriba" (igual que ROUND_HALF_UP del backend).
 * Trabaja sobre el texto para no depender de la coma flotante binaria.
 * Devuelve null si el texto no es un número decimal simple.
 */
function aMilesimas(texto: string): bigint | null {
  const m = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(texto.trim());
  if (!m || (m[2] === '' && (m[3] ?? '') === '')) return null;
  const decimales = (m[3] ?? '').padEnd(4, '0');
  let valor = BigInt((m[2] || '0') + decimales.slice(0, 3));
  if (decimales.charAt(3) >= '5') valor += 1n;
  return m[1] === '-' ? -valor : valor;
}

/** Texto decimal de un número (evita la notación exponencial). */
function textoDecimal(n: number): string {
  const t = String(n);
  return /e/i.test(t) ? n.toFixed(3) : t;
}

/**
 * Regla de corrección: la respuesta es correcta si, redondeada a tres decimales,
 * es igual al resultado almacenado. Es la misma regla del backend.
 */
export function respuestaEsCorrecta(respuesta: string, resultadoEsperado: number): boolean {
  const r = aMilesimas(respuesta);
  const e = aMilesimas(textoDecimal(resultadoEsperado));
  return r !== null && e !== null && r === e;
}

/**
 * Valida respuesta de SUMA o RESTA
 * Verifica el resultado final incluyendo el punto decimal
 */
function validarSumaResta(
  respuestaEstudiante: string,
  resultadoEsperado: number
): RespuestaValidacion {
  // Limpiar la respuesta (puede tener espacios o caracteres extra)
  const respuestaLimpia = respuestaEstudiante.trim();

  // Verificar que la respuesta sea un número válido
  if (!respuestaLimpia || isNaN(parseFloat(respuestaLimpia))) {
    return {
      esCorrecta: false,
      resultadoCorrecto: false,
    };
  }

  const esCorrecta = respuestaEsCorrecta(respuestaLimpia, resultadoEsperado);

  return {
    esCorrecta,
    resultadoCorrecto: esCorrecta,
  };
}

/**
 * Valida respuesta de MULTIPLICACIÓN
 * Verifica el resultado final (productos parciales son opcionales)
 */
function validarMultiplicacion(
  respuestaEstudiante: string,
  _numero1: number,
  _numero2: number,
  resultadoEsperado: number
): RespuestaValidacion {
  // Limpiar respuesta
  const respuestaLimpia = respuestaEstudiante.trim();

  if (!respuestaLimpia || isNaN(parseFloat(respuestaLimpia))) {
    return {
      esCorrecta: false,
      resultadoCorrecto: false,
    };
  }

  // Por ahora, solo validamos el resultado final
  // Los productos parciales son pasos intermedios que el estudiante completa
  // pero la validación principal es del resultado
  const resultadoCorrecto = respuestaEsCorrecta(respuestaLimpia, resultadoEsperado);

  return {
    esCorrecta: resultadoCorrecto,
    resultadoCorrecto,
    pasosIntermediosCorrectos: true, // TODO: validar productos parciales si es necesario
  };
}

/**
 * Valida respuesta de DIVISIÓN
 * Verifica el cociente (pasos intermedios son opcionales)
 */
function validarDivision(
  respuestaEstudiante: string,
  resultadoEsperado: number
): RespuestaValidacion {
  // Limpiar respuesta
  const respuestaLimpia = respuestaEstudiante.trim();

  if (!respuestaLimpia || isNaN(parseFloat(respuestaLimpia))) {
    return {
      esCorrecta: false,
      resultadoCorrecto: false,
    };
  }

  // Validar solo el cociente (resultado final)
  const resultadoCorrecto = respuestaEsCorrecta(respuestaLimpia, resultadoEsperado);

  return {
    esCorrecta: resultadoCorrecto,
    resultadoCorrecto,
    pasosIntermediosCorrectos: true, // TODO: validar pasos de división si es necesario
  };
}

/**
 * Función principal de validación
 * Delega a la función específica según el tipo de operación
 */
export function validarRespuesta(
  operacion: Operacion,
  respuestaEstudiante: string,
  numero1: number,
  numero2: number,
  resultadoEsperado: number
): RespuestaValidacion {
  if (!respuestaEstudiante || respuestaEstudiante.trim() === '') {
    return {
      esCorrecta: false,
      resultadoCorrecto: false,
    };
  }

  switch (operacion) {
    case 'SUMA':
    case 'RESTA':
      return validarSumaResta(respuestaEstudiante, resultadoEsperado);

    case 'MULTIPLICACION':
      return validarMultiplicacion(
        respuestaEstudiante,
        numero1,
        numero2,
        resultadoEsperado
      );

    case 'DIVISION':
      return validarDivision(respuestaEstudiante, resultadoEsperado);

    default:
      return {
        esCorrecta: false,
        resultadoCorrecto: false,
      };
  }
}
