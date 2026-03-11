/**
 * Generador determinista de pasos para explicar operaciones con decimales.
 *
 * Los pasos son genéricos (no temáticos, no LLM) y se calculan desde
 * los datos del problema en tiempo real.
 */

import type { Operacion } from '@/types';

export interface PasoAnimacion {
  titulo: string;
  descripcion: string;
}

function contarDecimales(num: number): number {
  const str = String(num);
  const idx = str.indexOf('.');
  return idx === -1 ? 0 : str.length - idx - 1;
}

function nombrePosicion(dec: number): string {
  if (dec === 1) return 'décimas';
  if (dec === 2) return 'centésimas';
  if (dec >= 3) return 'milésimas';
  return 'decimales';
}

function fmt(n: number, decimales: number): string {
  return decimales === 0 ? n.toFixed(0) : n.toFixed(decimales);
}

export function generarPasos(
  operacion: Operacion,
  num1: number,
  num2: number,
): PasoAnimacion[] {
  const dec1 = contarDecimales(num1);
  const dec2 = contarDecimales(num2);
  const maxDec = Math.max(dec1, dec2);
  const posicion = nombrePosicion(maxDec);

  switch (operacion) {
    case 'SUMA': {
      const resultado = parseFloat((num1 + num2).toFixed(maxDec + 1));
      const res = fmt(resultado, maxDec);
      return [
        {
          titulo: 'Alinea los decimales',
          descripcion: `Escribe ${num1} y debajo ${num2}. Los puntos decimales deben quedar uno exactamente encima del otro.`,
        },
        {
          titulo: `Empieza por la derecha`,
          descripcion: `Suma los dígitos de las ${posicion} (la columna más a la derecha). Si la suma es 10 o más, escribe solo el dígito de las unidades y "lleva 1" a la siguiente columna.`,
        },
        {
          titulo: 'Avanza hacia la izquierda',
          descripcion: `Suma los dígitos de la siguiente columna. Si llevaste 1 del paso anterior, súmalo aquí también. Repite para cada columna.`,
        },
        {
          titulo: 'Baja el punto decimal',
          descripcion: `Coloca el punto decimal en el resultado, alineado directamente debajo de los puntos decimales de los números originales.`,
        },
        {
          titulo: `Resultado: ${res}`,
          descripcion: `${num1} + ${num2} = ${res} ✓`,
        },
      ];
    }

    case 'RESTA': {
      const resultado = parseFloat((num1 - num2).toFixed(maxDec + 1));
      const res = fmt(resultado, maxDec);
      return [
        {
          titulo: 'Alinea los decimales',
          descripcion: `Escribe ${num1} arriba y ${num2} abajo, alineando los puntos decimales. Asegúrate de que cada dígito quede en su columna correcta.`,
        },
        {
          titulo: 'Empieza por la derecha',
          descripcion: `Resta los dígitos de las ${posicion}. Si el dígito de arriba es menor que el de abajo, pide "prestado 1" al vecino de la izquierda: el dígito de arriba se convierte en 10 + su valor.`,
        },
        {
          titulo: 'Avanza hacia la izquierda',
          descripcion: `Resta los dígitos de la siguiente columna. Si prestaste en el paso anterior, recuerda que ese dígito de arriba ya vale 1 menos. Repite para cada columna.`,
        },
        {
          titulo: 'Baja el punto decimal',
          descripcion: `Coloca el punto decimal en el resultado, alineado directamente debajo de los puntos decimales de los números originales.`,
        },
        {
          titulo: `Resultado: ${res}`,
          descripcion: `${num1} − ${num2} = ${res} ✓`,
        },
      ];
    }

    case 'MULTIPLICACION': {
      const totalDec = dec1 + dec2;
      const n1entero = Math.round(num1 * Math.pow(10, dec1));
      const n2entero = Math.round(num2 * Math.pow(10, dec2));
      const prodEntero = n1entero * n2entero;
      const resultado = parseFloat((num1 * num2).toFixed(totalDec + 1));
      const res = fmt(resultado, totalDec);
      return [
        {
          titulo: 'Cuenta los decimales totales',
          descripcion: `${num1} tiene ${dec1} decimal(es) y ${num2} tiene ${dec2} decimal(es). En total hay ${totalDec} decimal(es) — eso es cuántos tendrá la respuesta final.`,
        },
        {
          titulo: 'Multiplica como si fueran enteros',
          descripcion: `Ignora los puntos decimales por ahora. Multiplica: ${n1entero} × ${n2entero}.`,
        },
        {
          titulo: 'Multiplica dígito a dígito',
          descripcion: `Multiplica cada dígito de ${n2entero} por ${n1entero}. Cuando uses el segundo dígito, desplaza el resultado una posición a la izquierda.`,
        },
        {
          titulo: 'Suma los productos parciales',
          descripcion: `Suma todos los resultados intermedios. El total sin decimales es ${prodEntero}.`,
        },
        {
          titulo: 'Coloca el punto decimal',
          descripcion: `Desde la derecha de ${prodEntero}, cuenta ${totalDec} lugar(es) hacia la izquierda y coloca el punto decimal ahí.`,
        },
        {
          titulo: `Resultado: ${res}`,
          descripcion: `${num1} × ${num2} = ${res} ✓`,
        },
      ];
    }

    case 'DIVISION': {
      const resultado = parseFloat((num1 / num2).toFixed(2));
      const res = fmt(resultado, 2);
      const n2entero = Math.round(num2 * Math.pow(10, dec2));
      const n1ajustado = parseFloat((num1 * Math.pow(10, dec2)).toFixed(Math.max(0, dec1 - dec2)));
      return [
        {
          titulo: 'Escribe el problema',
          descripcion: `Divide ${num1} entre ${num2}. Prepara la división larga: el dividendo (${num1}) adentro y el divisor (${num2}) afuera.`,
        },
        {
          titulo: 'Convierte el divisor en entero',
          descripcion: `Mueve el punto decimal de ${num2} hacia la derecha ${dec2} lugar(es) para convertirlo en el número entero ${n2entero}.`,
        },
        {
          titulo: 'Ajusta el dividendo',
          descripcion: `Mueve el punto decimal de ${num1} el mismo número de lugares (${dec2} lugar(es)). El dividendo ahora es ${n1ajustado}.`,
        },
        {
          titulo: 'Divide normalmente',
          descripcion: `Calcula cuántas veces cabe ${n2entero} en ${n1ajustado}. Realiza la división larga paso a paso.`,
        },
        {
          titulo: `Resultado: ${res}`,
          descripcion: `${num1} ÷ ${num2} = ${res} ✓`,
        },
      ];
    }
  }
}
