import { useMemo } from 'react';

interface DivisionStep {
  productoStr: string;      // Producto del dígito del cociente por el divisor
  residuoStr: string;       // Residuo después de restar el producto
  espaciosProducto: number; // Offset para alinear el producto
  espaciosResiduo: number;  // Offset para alinear el residuo
  esDecimal?: boolean;      // Indica si este paso ya trabaja con decimales
  posicionDividendo?: number; // Posición en el dividendo normalizado hasta donde se ha avanzado
  dividendoParcialStr?: string; // Número que formamos (residuo anterior + dígitos bajados)
  espaciosDividendoParcial?: number; // Offset para el dividendo parcial
}

interface DivisionResult {
  cocienteStr: string;
  pasos: DivisionStep[];
  dividendoNormalizado: number;
  divisorNormalizado: number;
  metodo: 'escalamiento' | 'vertical' | 'normalizacion';
  dividendoDisplay: string;        // Para mostrar al usuario (con decimales originales)
  divisorDisplay: string;          // Para mostrar al usuario (con decimales originales)
  dividendoNormalizadoStr: string; // String normalizado para inputs (sin punto)
  divisorNormalizadoStr: string;   // String normalizado para inputs (sin punto)
  requiereNormalizacion: boolean;  // Si debe mostrar la sección de normalización
}

/**
 * Cuenta decimales en un número
 */
function contarDecimales(num: number): number {
  const str = num.toString();
  if (!str.includes('.')) return 0;
  return str.split('.')[1].length;
}

/**
 * MÉTODO 1: División por Escalamiento
 * Cuando dividendo tiene decimales pero divisor es natural
 * Ejemplo: 12.5 ÷ 5 = 125 ÷ 5 = 25, luego 25 ÷ 10 = 2.5
 */
function divisionPorEscalamiento(
  dividendo: number,
  divisor: number
): { dividendoN: number; divisorN: number; factor: number } {
  const decimalesDividendo = contarDecimales(dividendo);
  const factor = Math.pow(10, decimalesDividendo);

  return {
    dividendoN: Math.round(dividendo * factor),
    divisorN: divisor,
    factor,
  };
}

/**
 * MÉTODO 2: División Vertical con Decimales
 * Cuando el dividendo tiene decimales, dividimos normalmente y colocamos
 * la coma en el cociente cuando llegamos a las décimas
 *
 * Nota: Esta función está disponible para futuras extensiones pedagógicas
 * donde se quiera mostrar explícitamente dónde va la coma en el cociente
 */
// function divisionVerticalDecimal(
//   dividendoN: number,
//   decimalesDividendo: number
// ): { pasoDeLaComa: number } {
//   const dividendoStr = dividendoN.toString();
//   const digitosEnteros = dividendoStr.length - decimalesDividendo;
//   return {
//     pasoDeLaComa: digitosEnteros,
//   };
// }

/**
 * MÉTODO 3: Normalización del Divisor (Divisor Decimal)
 * Cuando el divisor tiene decimales, movemos la coma en ambos números
 * Ejemplo: 12.5 ÷ 2.5 → mover coma 1 posición → 125 ÷ 25
 * Ejemplo: 3.75 ÷ 1.5 → mover coma 1 posición → 37.5 ÷ 15 → 375 ÷ 150 (NO!)
 *          Correcto: necesitamos mover suficientes posiciones para eliminar TODOS los decimales
 */
function normalizarDivisor(
  dividendo: number,
  divisor: number
): { dividendoN: number; divisorN: number; posicionesMovidas: number } {
  const decimalesDividendo = contarDecimales(dividendo);
  const decimalesDivisor = contarDecimales(divisor);

  // Necesitamos mover la coma lo suficiente para eliminar todos los decimales
  // Si dividendo=3.75 (2 decimales) y divisor=1.5 (1 decimal)
  // Necesitamos mover 2 posiciones para eliminar ambos decimales
  const posicionesMovidas = Math.max(decimalesDividendo, decimalesDivisor);

  // Multiplicar ambos por el mismo factor
  const factor = Math.pow(10, posicionesMovidas);

  return {
    dividendoN: Math.round(dividendo * factor),
    divisorN: Math.round(divisor * factor),
    posicionesMovidas,
  };
}

/**
 * Determina qué método de división usar según los tipos de números
 */
function determinarMetodo(dividendo: number, divisor: number): 'escalamiento' | 'vertical' | 'normalizacion' {
  const decDividendo = contarDecimales(dividendo);
  const decDivisor = contarDecimales(divisor);

  if (decDivisor > 0) {
    // Si el divisor tiene decimales, normalizar
    return 'normalizacion';
  } else if (decDividendo > 0) {
    // Si solo el dividendo tiene decimales, división vertical
    return 'vertical';
  } else {
    // Ambos naturales (caso simple, pero puede usarse escalamiento si el cociente es decimal)
    return 'escalamiento';
  }
}

/**
 * Algoritmo de división larga paso a paso
 * Genera los pasos visuales pedagógicos para cualquier tipo de división
 *
 * IMPORTANTE: Este algoritmo trabaja bajando dígitos del dividendo
 * hasta formar un número >= divisor, luego divide
 */
function calcularPasosDivision(
  dividendoN: number,
  divisorN: number,
  cocienteEsperado: number,
  metodo: 'escalamiento' | 'vertical' | 'normalizacion',
  decimalesDividendo: number = 0
): DivisionStep[] {
  const dividendoStr = dividendoN.toString();
  // Redondear a 6 decimales para evitar strings como "5.999999999999999" por float
  const cocienteRedondeado = parseFloat(cocienteEsperado.toFixed(6));
  const cocienteStr = cocienteRedondeado.toString().replace('.', ''); // Sin punto
  const pasos: DivisionStep[] = [];

  let residuoActual = 0;
  let posicionDividendo = 0;

  // Determinar en qué paso colocar la coma (para división vertical)
  const digitosEnteros = dividendoStr.length - decimalesDividendo;

  // Iterar sobre cada dígito del cociente
  for (let i = 0; i < cocienteStr.length; i++) {
    const digitoCociente = parseInt(cocienteStr[i], 10);

    // PASO 1: Bajar dígitos del dividendo hasta tener suficiente
    // (necesitamos que residuoActual >= divisorN para poder dividir)
    while (residuoActual < divisorN && posicionDividendo < dividendoStr.length) {
      residuoActual = residuoActual * 10 + parseInt(dividendoStr[posicionDividendo], 10);
      posicionDividendo++;
    }

    // Si después de bajar todos los dígitos aún no alcanza, bajar un 0
    if (residuoActual < divisorN) {
      residuoActual = residuoActual * 10;
      posicionDividendo++;
    }

    // PASO 2: Calcular el producto (dígito del cociente × divisor)
    const producto = digitoCociente * divisorN;

    // PASO 3: Calcular el residuo después de restar
    const nuevoResiduo = residuoActual - producto;

    // Determinar si estamos en la parte decimal
    const esDecimal = metodo === 'vertical'
      ? posicionDividendo > digitosEnteros
      : false;

    // Calcular offset: el producto se alinea según el número de dígitos bajados.
    // IMPORTANTE: NO capamos posicionDividendo porque cuando "bajamos un 0 virtual"
    // (cociente decimal con dividendo entero, ej. 18÷5=3.6) posicionDividendo llega
    // a dividendoStr.length + 1 y ese valor es correcto para alinear el paso decimal.
    // Caparlo al length causaba que todos los pasos decimales quedasen en offset=0.
    const offsetProducto = Math.max(0, posicionDividendo - producto.toString().length);
    const offsetResiduo = Math.max(0, posicionDividendo - nuevoResiduo.toString().length);

    // El dividendo parcial es el número que formamos antes de dividir (residuoActual)
    const dividendoParcialStr = residuoActual.toString();
    const offsetDividendoParcial = Math.max(0, posicionDividendo - dividendoParcialStr.length);

    pasos.push({
      productoStr: producto.toString(),
      residuoStr: nuevoResiduo.toString(),
      espaciosProducto: offsetProducto,
      espaciosResiduo: offsetResiduo,
      esDecimal,
      posicionDividendo, // Guardar la posición actual en el dividendo
      dividendoParcialStr,
      espaciosDividendoParcial: offsetDividendoParcial,
    });

    // Actualizar residuo para el siguiente paso
    residuoActual = nuevoResiduo;

    // LÍMITE: Evitar loops infinitos en divisiones periódicas
    if (pasos.length > 10) break;
  }

  return pasos;
}

/**
 * Hook público para calcular división larga
 * Detecta automáticamente el mejor método pedagógico
 *
 * Para división vertical (dividendo con decimales):
 * - Muestra la división original con decimales
 * - Muestra el dividendo normalizado (escalado) sin decimales
 * - Todos los pasos se alinean con el dividendo normalizado
 */
export function useDivisionCalculator(
  dividendo: number,
  divisor: number,
  cocienteEsperado: number
) {
  return useMemo(() => {
    const metodo = determinarMetodo(dividendo, divisor);
    const decimalesDividendo = contarDecimales(dividendo);

    let dividendoN: number;
    let divisorN: number;

    // Aplicar el método correspondiente
    if (metodo === 'normalizacion') {
      // MÉTODO 3: Normalizar divisor (mover coma en ambos)
      const normalizado = normalizarDivisor(dividendo, divisor);
      dividendoN = normalizado.dividendoN;
      divisorN = normalizado.divisorN;

    } else if (metodo === 'vertical') {
      // MÉTODO 2: División vertical con decimales
      const escalado = divisionPorEscalamiento(dividendo, divisor);
      dividendoN = escalado.dividendoN;
      divisorN = escalado.divisorN;

    } else {
      // MÉTODO 1: Escalamiento simple (o naturales)
      dividendoN = Math.round(dividendo);
      divisorN = Math.round(divisor);
    }

    const pasos = calcularPasosDivision(
      dividendoN,
      divisorN,
      cocienteEsperado,
      metodo,
      decimalesDividendo
    );

    // NOTA: Ya NO ajustamos offsets para método vertical porque ahora mostramos
    // el dividendo normalizado explícitamente y todos los pasos se alinean con él
    // Los offsets calculados en calcularPasosDivision ya son correctos respecto al dividendo normalizado

    // Redondear el cociente para evitar representaciones float como "5.999999999999999"
    const cocienteDisplay = parseFloat(cocienteEsperado.toFixed(6)).toString();

    const result: DivisionResult = {
      cocienteStr: cocienteDisplay,
      pasos,
      dividendoNormalizado: dividendoN,
      divisorNormalizado: divisorN,
      metodo,
      dividendoDisplay: dividendo.toString(),
      divisorDisplay: divisor.toString(),
      dividendoNormalizadoStr: dividendoN.toString(),
      divisorNormalizadoStr: divisorN.toString(),
      requiereNormalizacion: metodo === 'normalizacion',
    };

    return result;
  }, [dividendo, divisor, cocienteEsperado]);
}
