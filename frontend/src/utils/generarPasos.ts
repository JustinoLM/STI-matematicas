/**
 * Generador determinista de pasos para explicar operaciones aritméticas.
 *
 * Cada operación muestra el procedimiento REAL con los números del problema:
 *  - SUMA/RESTA: columna a columna con acarreo/préstamo explícito
 *  - MULTIPLICACIÓN: productos parciales por dígito
 *  - DIVISIÓN: división larga paso a paso
 *
 * El número de pasos escala naturalmente con la complejidad del número:
 *  Nivel 1-2 → ~4-5 pasos | Nivel 3 → ~6-7 | Nivel 4 → ~8-9 | Nivel 5 → ~10
 */

import type { Operacion } from '@/types';

export interface PasoAnimacion {
  titulo: string;
  descripcion: string;
}

// ─── Utilidades internas ──────────────────────────────────────────────────────

function contarDecimales(num: number): number {
  const str = String(num);
  const idx = str.indexOf('.');
  return idx === -1 ? 0 : str.length - idx - 1;
}

function nombreColumna(posDesdeUnidades: number): string {
  switch (posDesdeUnidades) {
    case -3: return 'milésimas';
    case -2: return 'centésimas';
    case -1: return 'décimas';
    case  0: return 'unidades';
    case  1: return 'decenas';
    case  2: return 'centenas';
    case  3: return 'millares';
    default: return posDesdeUnidades < 0 ? 'decimales' : 'enteros';
  }
}

/** Representación limpia de un número: quita ceros finales sin quitar todos los decimales. */
function fmt(n: number, dec: number): string {
  return dec === 0 ? n.toFixed(0) : n.toFixed(dec);
}

// ─── SUMA ─────────────────────────────────────────────────────────────────────

function pasosSuma(num1: number, num2: number): PasoAnimacion[] {
  const dec1 = contarDecimales(num1);
  const dec2 = contarDecimales(num2);
  const maxDec = Math.max(dec1, dec2);

  // Representar ambos números con los mismos decimales y sin punto
  const n1str = num1.toFixed(maxDec).replace('.', '');
  const n2str = num2.toFixed(maxDec).replace('.', '');
  const len = Math.max(n1str.length, n2str.length);
  const n1pad = n1str.padStart(len, '0');
  const n2pad = n2str.padStart(len, '0');

  const pasos: PasoAnimacion[] = [];

  const n2display = maxDec > 0 ? num2.toFixed(maxDec) : String(num2);
  pasos.push({
    titulo: 'Alinea los números',
    descripcion: `Escribe ${num1} arriba y ${n2display} abajo, alineando los puntos decimales en una misma columna vertical.`,
  });

  // Procesar columnas de derecha a izquierda
  let carry = 0;
  const resultDigits: number[] = [];

  for (let i = len - 1; i >= 0; i--) {
    const d1 = parseInt(n1pad[i]);
    const d2 = parseInt(n2pad[i]);
    // posDesdeUnidades: negativo = decimal, 0 = unidades, positivo = entero mayor
    const pos = len - 1 - i - maxDec;
    const colNombre = nombreColumna(pos);

    const total = d1 + d2 + carry;
    const digit = total % 10;
    const nextCarry = Math.floor(total / 10);

    resultDigits.unshift(digit);

    const carryTexto = carry > 0 ? ` + ${carry} (llevado)` : '';
    const llevarTexto = nextCarry > 0 ? ' Lleva 1 a la columna de la izquierda.' : '';

    pasos.push({
      titulo: `Columna de ${colNombre}: ${d1} + ${d2}${carryTexto} = ${total}`,
      descripcion: `Escribe el ${digit}${llevarTexto}`,
    });

    carry = nextCarry;
  }

  if (carry > 0) {
    resultDigits.unshift(carry);
    pasos.push({
      titulo: `Dígito extra llevado: ${carry}`,
      descripcion: `Queda un ${carry} que no cabe. Escríbelo al inicio del resultado.`,
    });
  }

  if (maxDec > 0) {
    pasos.push({
      titulo: 'Baja el punto decimal',
      descripcion: `Coloca el punto decimal alineado con los de arriba (${maxDec} lugar${maxDec > 1 ? 'es' : ''} desde la derecha).`,
    });
  }

  const resultado = parseFloat((num1 + num2).toFixed(maxDec));
  const res = fmt(resultado, maxDec);
  pasos.push({
    titulo: `Resultado: ${res}`,
    descripcion: `${num1} + ${num2} = ${res} ✓`,
  });

  return pasos;
}

// ─── RESTA ────────────────────────────────────────────────────────────────────

function pasosResta(num1: number, num2: number): PasoAnimacion[] {
  const dec1 = contarDecimales(num1);
  const dec2 = contarDecimales(num2);
  const maxDec = Math.max(dec1, dec2);

  const n1str = num1.toFixed(maxDec).replace('.', '');
  const n2str = num2.toFixed(maxDec).replace('.', '');
  const len = Math.max(n1str.length, n2str.length);
  const n1pad = n1str.padStart(len, '0');
  const n2pad = n2str.padStart(len, '0');

  const pasos: PasoAnimacion[] = [];

  const n2display = maxDec > 0 ? num2.toFixed(maxDec) : String(num2);
  pasos.push({
    titulo: 'Alinea los números',
    descripcion: `Escribe ${num1} arriba y ${n2display} abajo, alineando los puntos decimales. El número mayor siempre va arriba.`,
  });

  let borrow = 0;
  const resultDigits: number[] = [];

  for (let i = len - 1; i >= 0; i--) {
    let d1 = parseInt(n1pad[i]) - borrow;
    const d2 = parseInt(n2pad[i]);
    const pos = len - 1 - i - maxDec;
    const colNombre = nombreColumna(pos);

    let digit: number;
    let nextBorrow: number;
    let borrowTexto = '';

    if (d1 < d2) {
      digit = d1 + 10 - d2;
      nextBorrow = 1;
      borrowTexto = ` Como ${d1} < ${d2}, pedimos prestado 10 al vecino de la izquierda. ${d1 + 10} − ${d2} = ${digit}.`;
    } else {
      digit = d1 - d2;
      nextBorrow = 0;
    }

    resultDigits.unshift(digit);

    const prestamoIn = borrow > 0 ? ` (ya habíamos prestado 1, así que arriba teníamos ${parseInt(n1pad[i])}−1=${d1})` : '';
    pasos.push({
      titulo: `Columna de ${colNombre}: ${d1} − ${d2} = ${digit}`,
      descripcion: prestamoIn + borrowTexto || `Escribe el ${digit}.`,
    });

    borrow = nextBorrow;
  }

  if (maxDec > 0) {
    pasos.push({
      titulo: 'Baja el punto decimal',
      descripcion: `Coloca el punto decimal alineado con los de arriba (${maxDec} lugar${maxDec > 1 ? 'es' : ''} desde la derecha).`,
    });
  }

  const resultado = parseFloat((num1 - num2).toFixed(maxDec));
  const res = fmt(resultado, maxDec);
  pasos.push({
    titulo: `Resultado: ${res}`,
    descripcion: `${num1} − ${num2} = ${res} ✓`,
  });

  return pasos;
}

// ─── MULTIPLICACIÓN ───────────────────────────────────────────────────────────

function pasosMultiplicacion(num1: number, num2: number): PasoAnimacion[] {
  const dec1 = contarDecimales(num1);
  const dec2 = contarDecimales(num2);
  const totalDec = dec1 + dec2;

  const n1entero = Math.round(num1 * Math.pow(10, dec1));
  const n2entero = Math.round(num2 * Math.pow(10, dec2));

  const pasos: PasoAnimacion[] = [];

  // Paso 1: contar decimales
  pasos.push({
    titulo: 'Cuenta los decimales totales',
    descripcion: `${num1} tiene ${dec1} decimal(es) y ${num2} tiene ${dec2}. Total: ${totalDec} decimal(es). La respuesta final también tendrá ${totalDec} decimal(es).`,
  });

  // Paso 2: convertir a enteros
  if (totalDec > 0) {
    pasos.push({
      titulo: `Trabaja con enteros: ${n1entero} × ${n2entero}`,
      descripcion: `Ignora los puntos decimales por ahora. Multiplica ${n1entero} × ${n2entero} como si fueran números enteros.`,
    });
  }

  // Paso 3+: productos parciales por cada dígito de n2entero
  const n2digits = String(n2entero).split('').reverse(); // de menos a más significativo
  const productosParcialesNombres: string[] = [];
  let productoTotal = 0;

  for (let i = 0; i < n2digits.length; i++) {
    const dígito = parseInt(n2digits[i]);
    const parcial = n1entero * dígito;
    const desplazado = parcial * Math.pow(10, i);
    productoTotal += desplazado;
    productosParcialesNombres.push(String(desplazado));

    const posNombre = i === 0 ? 'unidades' : i === 1 ? 'decenas' : i === 2 ? 'centenas' : 'millares';
    const desplTexto = i > 0 ? ` Agrega ${i} cero(s) al final porque este dígito está en las ${posNombre}: ${desplazado}.` : '';

    pasos.push({
      titulo: `Multiplica por el dígito de ${posNombre}: ${n1entero} × ${dígito} = ${parcial}`,
      descripcion: `Escribe el resultado parcial debajo.${desplTexto}`,
    });
  }

  // Paso: sumar productos parciales (solo si hay más de un dígito en n2)
  if (n2digits.length > 1) {
    pasos.push({
      titulo: `Suma los productos parciales`,
      descripcion: `${productosParcialesNombres.join(' + ')} = ${productoTotal}`,
    });
  }

  // Paso: colocar punto decimal
  if (totalDec > 0) {
    const resultado = parseFloat((num1 * num2).toFixed(totalDec));
    const res = fmt(resultado, totalDec);
    pasos.push({
      titulo: `Coloca el punto decimal`,
      descripcion: `Desde la derecha de ${productoTotal}, cuenta ${totalDec} lugar${totalDec > 1 ? 'es' : ''} hacia la izquierda y pon el punto decimal.`,
    });
    pasos.push({
      titulo: `Resultado: ${res}`,
      descripcion: `${num1} × ${num2} = ${res} ✓`,
    });
  } else {
    pasos.push({
      titulo: `Resultado: ${productoTotal}`,
      descripcion: `${num1} × ${num2} = ${productoTotal} ✓`,
    });
  }

  return pasos;
}

// ─── DIVISIÓN ─────────────────────────────────────────────────────────────────

function pasosDivision(num1: number, num2: number, nivel: number): PasoAnimacion[] {
  const dec2 = contarDecimales(num2);
  const dec1 = contarDecimales(num1);

  const pasos: PasoAnimacion[] = [];

  pasos.push({
    titulo: 'Plantea la división larga',
    descripcion: `Escribe ${num1} como dividendo (adentro) y ${num2} como divisor (afuera). Resolveremos cuántas veces cabe ${num2} en ${num1}.`,
  });

  // Convertir divisor a entero si tiene decimales
  let divisor: number;
  let dividendo: number;

  if (dec2 > 0) {
    divisor = Math.round(num2 * Math.pow(10, dec2));
    dividendo = parseFloat((num1 * Math.pow(10, dec2)).toFixed(Math.max(0, dec1 - dec2)));
    pasos.push({
      titulo: `Elimina el decimal del divisor`,
      descripcion: `Mueve el punto ${dec2} lugar${dec2 > 1 ? 'es' : ''} a la derecha en ambos: ${num2} → ${divisor} y ${num1} → ${dividendo}. Ahora dividimos ${dividendo} ÷ ${divisor}.`,
    });
  } else {
    divisor = num2;
    dividendo = num1;
  }

  // Construir string de dígitos del dividendo
  const divDec = contarDecimales(dividendo);
  const dividendoStr = dividendo.toFixed(divDec).replace('.', '');
  const intDigitCount = dividendoStr.length - divDec; // cuántos dígitos son parte entera

  // Ejecutar la división larga
  interface DivStep { current: number; q: number; product: number; rem: number; esDecimal: boolean }
  const divSteps: DivStep[] = [];
  let remainder = 0;

  for (let i = 0; i < dividendoStr.length; i++) {
    const d = parseInt(dividendoStr[i]);
    const current = remainder * 10 + d;
    const q = Math.floor(current / divisor);
    const product = q * divisor;
    remainder = current - product;
    divSteps.push({ current, q, product, rem: remainder, esDecimal: i >= intDigitCount });
  }

  // Si queda resto y el dividendo era entero, agregar pasos decimales
  if (remainder > 0 && divDec === 0) {
    const extraSteps = nivel >= 4 ? 3 : nivel >= 3 ? 2 : 1;
    for (let i = 0; i < extraSteps && remainder > 0; i++) {
      const current = remainder * 10;
      const q = Math.floor(current / divisor);
      const product = q * divisor;
      remainder = current - product;
      divSteps.push({ current, q, product, rem: remainder, esDecimal: true });
    }
  }

  // Filtrar pasos triviales al inicio (current < divisor con q=0)
  let start = 0;
  while (start < divSteps.length - 1 && divSteps[start].q === 0 && divSteps[start].current < divisor) {
    start++;
  }

  // Generar pasos de la división
  for (let i = start; i < divSteps.length; i++) {
    const s = divSteps[i];
    const esUltimo = i === divSteps.length - 1;
    const bajarTexto = !esUltimo && s.rem > 0 ? ` Baja el siguiente dígito.` : '';
    pasos.push({
      titulo: `${s.current} ÷ ${divisor} = ${s.q}`,
      descripcion: `${s.q} × ${divisor} = ${s.product}. Resta: ${s.current} − ${s.product} = ${s.rem}.${bajarTexto}`,
    });
  }

  // Punto decimal en el cociente
  if (divDec > 0) {
    pasos.push({
      titulo: 'Ubica el punto decimal en el cociente',
      descripcion: `El dividendo ${dividendo} tiene ${divDec} decimal(es): el punto va después del ${intDigitCount}° dígito del cociente.`,
    });
  } else if (divSteps.some(s => s.esDecimal)) {
    pasos.push({
      titulo: 'Coloca el punto decimal',
      descripcion: `Al necesitar bajar un 0 para continuar, ya pasamos a los decimales del cociente. Marca el punto ahí.`,
    });
  }

  const resultado = num1 / num2;
  const resDec = Math.max(divDec, nivel >= 3 ? 2 : 1);
  const res = parseFloat(resultado.toFixed(resDec + 1)).toFixed(resDec);
  pasos.push({
    titulo: `Resultado: ${parseFloat(res)}`,
    descripcion: `${num1} ÷ ${num2} = ${parseFloat(res)} ✓`,
  });

  return pasos;
}

// ─── Función principal exportada ──────────────────────────────────────────────

export function generarPasos(
  operacion: Operacion,
  num1: number,
  num2: number,
  nivel: number = 1,
): PasoAnimacion[] {
  switch (operacion) {
    case 'SUMA':
      return pasosSuma(num1, num2);
    case 'RESTA':
      return pasosResta(num1, num2);
    case 'MULTIPLICACION':
      return pasosMultiplicacion(num1, num2);
    case 'DIVISION':
      return pasosDivision(num1, num2, nivel);
    default:
      return [];
  }
}
