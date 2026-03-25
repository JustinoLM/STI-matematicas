import { useMemo } from 'react';

interface ProductoParcial {
  valor: number;
  valorStr: string;
  valorStrVisual: string; // valorStr con celda vacía insertada en la columna decimal (si aplica)
  espacios: number; // celdas vacías a la derecha
}

interface MultiplicationResult {
  multiplicandoStr: string;   // solo para cálculo interno
  multiplicadorStr: string;   // solo para cálculo interno
  productosParciales: ProductoParcial[];
  resultadoStr: string;       // con punto decimal insertado
  totalDecimales: number;
}

/**
 * Contar decimales reales de un número
 */
function contarDecimales(num: number): number {
  const str = num.toString();
  if (!str.includes('.')) return 0;
  return str.split('.')[1].length;
}

/**
 * Usar normalización por string (sin errores de precisión)
 */
function normalizarDecimal(num: number, decimales: number): number {
  return Number(num.toFixed(decimales).replace('.', ''));
}


/**
 * Inserta el punto decimal según la cantidad total de decimales
 */
function insertarDecimal(valor: number, totalDecimales: number): string {
  let str = valor.toString();

  if (totalDecimales === 0) return str;

  const pos = str.length - totalDecimales;

  return pos > 0
    ? str.slice(0, pos) + '.' + str.slice(pos)
    : '0.' + '0'.repeat(Math.abs(pos)) + str;
}

/**
 * Calcula productos parciales para multiplicación larga
 */
function calcularProductosParciales(
  multiplicando: number,
  multiplicador: number
): MultiplicationResult {
  const dec1 = contarDecimales(multiplicando);
  const dec2 = contarDecimales(multiplicador);
  const totalDecimales = dec1 + dec2;

  // Normalización correcta
  const m1 = normalizarDecimal(multiplicando, dec1);
  const m2 = normalizarDecimal(multiplicador, dec2);

  const multiplicandoStr = m1.toString();
  const multiplicadorStr = m2.toString();

  // Resultado final (necesario antes de calcular valorStrVisual de parciales)
  const resultadoEntero = m1 * m2;
  const resultadoStr = insertarDecimal(resultadoEntero, totalDecimales);

  const productosParciales: ProductoParcial[] = [];

  // Productos parciales (de unidades hacia arriba, como en el método tradicional)
  for (let i = multiplicadorStr.length - 1; i >= 0; i--) {
    const digito = parseInt(multiplicadorStr[i], 10);
    const producto = m1 * digito;
    const espacios = multiplicadorStr.length - 1 - i; // Unidades=0, decenas=1, centenas=2

    const valorStr = producto.toString();

    // Insertar celda vacía en la columna del decimal cuando el parcial la atraviesa.
    // Fórmula: insertIdx = decimalIdx + valorStr.length + espacios - resultadoStr.length + 1
    // Solo se aplica cuando 0 < insertIdx <= valorStr.length
    let valorStrVisual = valorStr;
    const decimalIdx = resultadoStr.indexOf('.');
    if (decimalIdx >= 0) {
      const insertIdx = decimalIdx + valorStr.length + espacios - resultadoStr.length + 1;
      if (insertIdx > 0 && insertIdx <= valorStr.length) {
        valorStrVisual = valorStr.slice(0, insertIdx) + ' ' + valorStr.slice(insertIdx);
      }
    }

    productosParciales.push({
      valor: producto,
      valorStr,
      valorStrVisual,
      espacios,
    });
  }

  return {
    multiplicandoStr,
    multiplicadorStr,
    productosParciales,
    resultadoStr,
    totalDecimales,
  };
}

/**
 * Hook público
 */
export function useMultiplicationCalculator(
  multiplicando: number,
  multiplicador: number
) {
  return useMemo(
    () => calcularProductosParciales(multiplicando, multiplicador),
    [multiplicando, multiplicador]
  );
}
