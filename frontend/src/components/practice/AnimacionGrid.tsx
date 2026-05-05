/**
 * Grid de demostración paso a paso — espeja el layout de los grids reales
 * (SumaRestaGrid, MultiplicacionGrid, DivisionGrid) pero con celdas de solo
 * lectura pre-rellenas que se revelan progresivamente con pasoActual.
 *
 * Para cada operación muestra las celdas intermedias auxiliares:
 *  - SUMA:   fila de acarreos sobre num1
 *  - RESTA:  fila de préstamos sobre num1
 *  - MULT:   productos parciales por cada dígito del multiplicador
 *  - DIV:    divisiones largas (dividendo parcial → producto → línea → residuo)
 */

import { useMemo } from 'react';
import { useMultiplicationCalculator } from '@/hooks/useMultiplicationCalculator';
import { useDivisionCalculator } from '@/hooks/useDivisionCalculator';
import type { Operacion } from '@/types';

// ─── Constantes de layout ─────────────────────────────────────────────────────

/** Ancho de N celdas + gaps (idéntico al usado en los grids reales) */
const cw = (n: number) => `calc(${n} * 2.75rem)`;

// ─── Utilidades ───────────────────────────────────────────────────────────────

function countDec(n: number): number {
  const s = n.toString();
  return s.includes('.') ? s.split('.')[1].length : 0;
}

function alignDecimals(num1: number, num2: number): { a1: string; a2: string; maxDec: number } {
  const d1 = countDec(num1);
  const d2 = countDec(num2);
  const maxDec = Math.max(d1, d2);
  const pad = (s: string, dec: number) =>
    dec >= maxDec ? s : dec === 0 ? `${s}.${'0'.repeat(maxDec)}` : `${s}${'0'.repeat(maxDec - dec)}`;
  return { a1: pad(num1.toString(), d1), a2: pad(num2.toString(), d2), maxDec };
}

function calcResult(op: Operacion, n1: number, n2: number): string {
  const d1 = countDec(n1);
  const d2 = countDec(n2);
  const maxDec = Math.max(d1, d2);
  switch (op) {
    case 'SUMA': {
      const r = parseFloat((n1 + n2).toFixed(maxDec + 1));
      return maxDec === 0 ? r.toFixed(0) : r.toFixed(maxDec);
    }
    case 'RESTA': {
      const r = parseFloat((n1 - n2).toFixed(maxDec + 1));
      return maxDec === 0 ? r.toFixed(0) : r.toFixed(maxDec);
    }
    case 'MULTIPLICACION': {
      const td = d1 + d2;
      const r = parseFloat((n1 * n2).toFixed(td + 1));
      return td === 0 ? r.toFixed(0) : r.toFixed(td);
    }
    case 'DIVISION': {
      const r = parseFloat((n1 / n2).toFixed(2));
      return r % 1 === 0 ? r.toFixed(0) : r.toFixed(2);
    }
  }
}

// ─── Celdas atómicas ──────────────────────────────────────────────────────────

function StaticCell({ char }: { char: string }) {
  if (char === '.') {
    return <span className="w-4 h-10 flex items-end justify-center pb-1 font-bold text-2xl text-gray-800">.</span>;
  }
  return <span className="w-10 h-10 flex items-center justify-center font-bold text-2xl text-gray-800">{char}</span>;
}

interface RevealedCellProps {
  char: string;
  revealed: boolean;
  isComplete: boolean;
}

function RevealedCell({ char, revealed, isComplete }: RevealedCellProps) {
  if (char === '.') {
    return (
      <span className="w-4 h-10 flex items-end justify-center pb-1 font-bold text-2xl text-gray-700">.</span>
    );
  }
  return (
    <span
      className={[
        'w-10 h-10 flex items-center justify-center font-bold text-2xl border-2 rounded transition-all duration-400',
        revealed && isComplete
          ? 'bg-green-100 text-green-700 border-green-400'
          : revealed
          ? 'bg-blue-50 text-blue-800 border-blue-300'
          : 'bg-gray-50 text-transparent border-gray-200',
      ].join(' ')}
    >
      {revealed ? char : '·'}
    </span>
  );
}

/** Celda auxiliar pequeña (acarreo / préstamo / dígito intermedio) */
function AuxCell({ value, revealed, color = 'blue' }: { value: string; revealed: boolean; color?: 'blue' | 'purple' }) {
  const colors = {
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    purple: 'text-purple-600 bg-purple-50 border-purple-200',
  };
  return (
    <span
      className={[
        'w-10 h-7 flex items-center justify-center text-sm font-bold border rounded transition-all duration-400',
        revealed && value !== '' && value !== '0'
          ? colors[color]
          : 'text-transparent border-transparent bg-transparent',
      ].join(' ')}
    >
      {revealed && value !== '0' ? value : ''}
    </span>
  );
}

function HLine({ width }: { width: string }) {
  return <div className="border-t-2 border-gray-600 mt-1" style={{ width }} />;
}

// ─── Cómputos de acarreos (SUMA) ─────────────────────────────────────────────

function computeCarriesSuma(n1pad: string, n2pad: string): number[] {
  const n = n1pad.length;
  const carriesInto = new Array(n).fill(0);
  let c = 0;
  for (let i = n - 1; i >= 0; i--) {
    const total = parseInt(n1pad[i]) + parseInt(n2pad[i]) + c;
    c = Math.floor(total / 10);
    if (i > 0) carriesInto[i - 1] = c;
  }
  return carriesInto; // carriesInto[j] = carry INTO column j from column j+1
}

function computeBorrowsResta(n1pad: string, n2pad: string): number[] {
  // borrowFrom[j] = 1 si la columna j tuvo que prestar a su vecino de la derecha
  const n = n1pad.length;
  const borrowFrom = new Array(n).fill(0);
  let borrow = 0;
  for (let i = n - 1; i >= 0; i--) {
    const d1eff = parseInt(n1pad[i]) - borrow;
    const d2 = parseInt(n2pad[i]);
    if (d1eff < d2) {
      borrow = 1;
      if (i > 0) borrowFrom[i - 1] = 1; // column i-1 is borrowed from
    } else {
      borrow = 0;
    }
  }
  return borrowFrom;
}

// ─── Fila de resultado con revelación por paso ────────────────────────────────

/**
 * Para una cadena de resultado y un string de referencia (mismo largo, sin decimal),
 * calcula en qué paso (1-indexed) se revela cada dígito (de derecha a izquierda).
 */
function buildRevealMap(resultStr: string, n: number): number[] {
  // resultStr may include '.'
  // Returns array where revealMap[displayIdx] = paso at which it's revealed
  const chars = resultStr.split('');
  let nonDecFromLeft = 0;
  return chars.map((c) => {
    if (c === '.') return 0; // decimal always shown
    const step = n - nonDecFromLeft; // rightmost (ndIdx=n-1) → step 1, leftmost → step n
    nonDecFromLeft++;
    return step;
  });
}

// ─── SUMA ─────────────────────────────────────────────────────────────────────

function AnimSuma({ num1, num2, pasoActual, totalPasos }: {
  num1: number; num2: number; pasoActual: number; totalPasos: number;
}) {
  const { a1, a2 } = alignDecimals(num1, num2);

  const { n, carriesInto, extraCarry, resultStr, revealMap } = useMemo(() => {
    const nd1 = a1.replace('.', '');
    const nd2 = a2.replace('.', '');
    const n = Math.max(nd1.length, nd2.length);
    const n1pad = nd1.padStart(n, '0');
    const n2pad = nd2.padStart(n, '0');
    const carriesInto = computeCarriesSuma(n1pad, n2pad);
    // Extra carry from leftmost column
    let c = 0;
    for (let i = n - 1; i >= 0; i--) {
      const total = parseInt(n1pad[i]) + parseInt(n2pad[i]) + c;
      c = Math.floor(total / 10);
    }
    const extraCarry = c;
    const resultStr = calcResult('SUMA', num1, num2);
    const revealMap = buildRevealMap(resultStr, n);
    return { n, carriesInto, extraCarry, resultStr, revealMap };
  }, [a1, a2, num1, num2]);

  const isComplete = pasoActual >= totalPasos - 1;
  const a1Chars = a1.split('');
  const maxLen = Math.max(a1.length, a2.length, resultStr.length);

  // Map display position in a1 to nonDecIdx
  function getNdIdx(dp: number): number {
    let count = 0;
    for (let i = 0; i < dp; i++) if (a1Chars[i] !== '.') count++;
    return count;
  }

  return (
    <div className="flex flex-col items-end gap-1 font-mono">
      {/* Fila de acarreos */}
      <div className="flex flex-col items-end">
        <span className="text-xs text-gray-400 mb-1 font-sans">Acarreos</span>
        <div className="flex gap-1 justify-end" style={{ width: cw(maxLen) }}>
          {extraCarry > 0 && (
            <AuxCell
              value={String(extraCarry)}
              revealed={pasoActual >= n + 1}
              color="blue"
            />
          )}
          {a1Chars.map((char, dp) => {
            if (char === '.') return <span key={dp} className="w-4 h-7" />;
            const ndIdx = getNdIdx(dp);
            const carry = carriesInto[ndIdx] ?? 0;
            const step = n - ndIdx;
            return (
              <AuxCell key={dp} value={String(carry)} revealed={pasoActual >= step} color="blue" />
            );
          })}
        </div>
      </div>

      {/* Num1 */}
      <div className="flex gap-1 justify-end" style={{ width: cw(maxLen) }}>
        {a1Chars.map((c, i) => <StaticCell key={i} char={c} />)}
      </div>

      {/* Operador + Num2 */}
      <div className="flex items-center gap-2 justify-end">
        <span className="font-bold text-2xl text-gray-500 w-6 text-right">+</span>
        <div className="flex gap-1">
          {a2.split('').map((c, i) => <StaticCell key={i} char={c} />)}
        </div>
      </div>

      <HLine width={cw(maxLen)} />

      {/* Resultado */}
      <div className="flex gap-1">
        {resultStr.split('').map((char, dp) => (
          <RevealedCell key={dp} char={char} revealed={pasoActual >= revealMap[dp]} isComplete={isComplete} />
        ))}
      </div>
    </div>
  );
}

// ─── RESTA ────────────────────────────────────────────────────────────────────

function AnimResta({ num1, num2, pasoActual, totalPasos }: {
  num1: number; num2: number; pasoActual: number; totalPasos: number;
}) {
  const { a1, a2 } = alignDecimals(num1, num2);

  const { n, borrowFrom, resultStr, revealMap, a1Chars } = useMemo(() => {
    const nd1 = a1.replace('.', '');
    const nd2 = a2.replace('.', '');
    const n = Math.max(nd1.length, nd2.length);
    const n1pad = nd1.padStart(n, '0');
    const n2pad = nd2.padStart(n, '0');
    const borrowFrom = computeBorrowsResta(n1pad, n2pad);
    const resultStr = calcResult('RESTA', num1, num2);
    const revealMap = buildRevealMap(resultStr, n);
    return { n, borrowFrom, resultStr, revealMap, a1Chars: a1.split('') };
  }, [a1, a2, num1, num2]);

  const isComplete = pasoActual >= totalPasos - 1;
  const maxLen = Math.max(a1.length, a2.length, resultStr.length);

  function getNdIdx(dp: number): number {
    let count = 0;
    for (let i = 0; i < dp; i++) if (a1Chars[i] !== '.') count++;
    return count;
  }

  return (
    <div className="flex flex-col items-end gap-1 font-mono">
      {/* Fila de préstamos */}
      <div className="flex flex-col items-end">
        <span className="text-xs text-gray-400 mb-1 font-sans">Préstamos</span>
        <div className="flex gap-1 justify-end" style={{ width: cw(maxLen) }}>
          {a1Chars.map((char, dp) => {
            if (char === '.') return <span key={dp} className="w-4 h-7" />;
            const ndIdx = getNdIdx(dp);
            const borrowed = borrowFrom[ndIdx] ?? 0;
            const step = n - ndIdx;
            return (
              <AuxCell key={dp} value={borrowed ? '−1' : ''} revealed={pasoActual >= step} color="purple" />
            );
          })}
        </div>
      </div>

      {/* Num1 */}
      <div className="flex gap-1 justify-end" style={{ width: cw(maxLen) }}>
        {a1Chars.map((c, i) => <StaticCell key={i} char={c} />)}
      </div>

      {/* Operador + Num2 */}
      <div className="flex items-center gap-2 justify-end">
        <span className="font-bold text-2xl text-gray-500 w-6 text-right">−</span>
        <div className="flex gap-1">
          {a2.split('').map((c, i) => <StaticCell key={i} char={c} />)}
        </div>
      </div>

      <HLine width={cw(maxLen)} />

      {/* Resultado */}
      <div className="flex gap-1">
        {resultStr.split('').map((char, dp) => (
          <RevealedCell key={dp} char={char} revealed={pasoActual >= revealMap[dp]} isComplete={isComplete} />
        ))}
      </div>
    </div>
  );
}

// ─── MULTIPLICACIÓN ───────────────────────────────────────────────────────────

function AnimMultiplicacion({ num1, num2, pasoActual, totalPasos }: {
  num1: number; num2: number; pasoActual: number; totalPasos: number;
}) {
  const { productosParciales, resultadoStr } = useMultiplicationCalculator(num1, num2);

  const d1 = countDec(num1);
  const d2 = countDec(num2);
  const totalDec = d1 + d2;

  // Step at which the first partial product appears
  const firstPartialStep = totalDec > 0 ? 2 : 1;
  const M = productosParciales.length;

  const isComplete = pasoActual >= totalPasos - 1;
  // Result row appears at the "suma parciales" step or later (after all partials)
  const resultStep = firstPartialStep + M; // "Suma parciales" or single product result

  const maxWidth = resultadoStr.length + Math.max(...productosParciales.map((p) => p.espacios));

  return (
    <div className="flex flex-col items-end gap-1 font-mono">
      {/* Num1 */}
      <div className="flex gap-1">
        {num1.toString().split('').map((c, i) => <StaticCell key={i} char={c} />)}
      </div>

      {/* Operador + Num2 */}
      <div className="flex items-center gap-2">
        <span className="font-bold text-2xl text-gray-500 w-6 text-right">×</span>
        <div className="flex gap-1">
          {num2.toString().split('').map((c, i) => <StaticCell key={i} char={c} />)}
        </div>
      </div>

      <HLine width={cw(maxWidth)} />

      {/* Productos parciales */}
      <div className="flex flex-col items-end gap-1">
        {productosParciales.map((parcial, j) => {
          const revealed = pasoActual >= firstPartialStep + j;
          return (
            <div key={j} className="flex gap-1">
              {parcial.valorStrVisual.split('').map((char, ci) => (
                char === ' '
                  ? <span key={ci} className="w-10 h-10" />
                  : <RevealedCell
                      key={ci}
                      char={char}
                      revealed={revealed}
                      isComplete={false}
                    />
              ))}
              {/* Celdas vacías a la derecha (espacios) */}
              {Array.from({ length: parcial.espacios }).map((_, si) => (
                <span key={`sp-${si}`} className="w-10 h-10" />
              ))}
            </div>
          );
        })}
      </div>

      {/* Línea final (aparece cuando todos los parciales están) */}
      {pasoActual >= firstPartialStep + M - 1 && (
        <HLine width={cw(maxWidth)} />
      )}

      {/* Resultado final */}
      <div className="flex gap-1">
        {resultadoStr.split('').map((char, i) => (
          <RevealedCell
            key={i}
            char={char}
            revealed={pasoActual >= resultStep}
            isComplete={isComplete}
          />
        ))}
      </div>
    </div>
  );
}

// ─── DIVISIÓN ─────────────────────────────────────────────────────────────────

function AnimDivision({ num1, num2, pasoActual, totalPasos }: {
  num1: number; num2: number; pasoActual: number; totalPasos: number;
}) {
  const resultado = num1 / num2;
  const {
    cocienteStr,
    pasos,
    dividendoNormalizadoStr,
    divisorNormalizadoStr,
    requiereNormalizacion,
  } = useDivisionCalculator(num1, num2, resultado);

  const dividendoStr = num1.toString();
  const divisorStr = num2.toString();
  const esMetodoVertical = dividendoStr.includes('.') && !divisorStr.includes('.');

  const dec2 = countDec(num2);
  // First division paso step (from generarPasos):
  // Step 0 = "Plantea", step 1 = "Elimina decimal" if dec2>0, then division pasos
  const firstDivStep = dec2 > 0 ? 2 : 1;
  const isComplete = pasoActual >= totalPasos - 1;

  // How many quotient digits to show
  const quotientRevealed = Math.max(0, pasoActual - firstDivStep + 1);

  return (
    <div className="flex flex-col items-start gap-1 font-mono text-xl">
      {/* División original */}
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {dividendoStr.split('').map((d, i) => (
            <StaticCell key={i} char={d} />
          ))}
        </div>
        <span className="font-bold text-2xl text-gray-500">÷</span>
        <div className="flex gap-1">
          {divisorStr.split('').map((d, i) => (
            <StaticCell key={i} char={d} />
          ))}
        </div>
        <span className="font-bold text-xl text-gray-500">=</span>
        {/* Cociente revelado dígito a dígito */}
        <div className="flex gap-1">
          {cocienteStr.split('').map((c, i) => (
            <RevealedCell
              key={i}
              char={c}
              revealed={i < quotientRevealed}
              isComplete={isComplete}
            />
          ))}
        </div>
      </div>

      {/* Normalización si aplica */}
      {(requiereNormalizacion || esMetodoVertical) && pasoActual >= 1 && (
        <div className="mt-1 space-y-1">
          <span className="text-xs text-gray-500 font-sans">
            {requiereNormalizacion
              ? `Normalizado: ${dividendoNormalizadoStr} ÷ ${divisorNormalizadoStr}`
              : `Dividendo escalado: ${dividendoNormalizadoStr}`}
          </span>
        </div>
      )}

      {/* Línea divisoria horizontal */}
      <HLine width={cw(dividendoNormalizadoStr.length || dividendoStr.length)} />

      {/* Pasos de la división larga */}
      <div className="space-y-1">
        {pasos.map((paso, idx) => {
          const revealed = pasoActual >= firstDivStep + idx;
          if (!revealed) return null;

          return (
            <div key={idx} className="space-y-0.5">
              {/* Dividendo parcial (desde el segundo paso en adelante) */}
              {idx > 0 && paso.dividendoParcialStr && (
                <div
                  className="flex gap-1"
                  style={{ paddingLeft: cw(paso.espaciosDividendoParcial ?? 0) }}
                >
                  {paso.dividendoParcialStr.split('').map((c, ci) => (
                    <RevealedCell key={ci} char={c} revealed={true} isComplete={false} />
                  ))}
                </div>
              )}

              {/* Producto */}
              <div
                className="flex gap-1"
                style={{ paddingLeft: cw(paso.espaciosProducto ?? 0) }}
              >
                {paso.productoStr.split('').map((c, ci) => (
                  <RevealedCell key={ci} char={c} revealed={true} isComplete={false} />
                ))}
              </div>

              {/* Línea de resta */}
              <div style={{ marginLeft: cw(paso.espaciosProducto ?? 0) }}>
                <HLine width={cw(paso.productoStr.length)} />
              </div>

              {/* Residuo (solo en el último paso) */}
              {idx === pasos.length - 1 && (
                <div
                  className="flex gap-1"
                  style={{ paddingLeft: cw(paso.espaciosResiduo ?? 0) }}
                >
                  {paso.residuoStr.split('').map((c, ci) => (
                    <RevealedCell
                      key={ci}
                      char={c}
                      revealed={true}
                      isComplete={isComplete}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

interface AnimacionGridProps {
  operacion: Operacion;
  numero1: number;
  numero2: number;
  pasoActual: number;
  totalPasos: number;
}

export function AnimacionGrid({
  operacion,
  numero1,
  numero2,
  pasoActual,
  totalPasos,
}: AnimacionGridProps) {
  return (
    <div className="bg-white rounded-xl border-2 border-gray-100 p-6 flex items-center justify-center min-h-[150px] overflow-x-auto">
      {(operacion === 'SUMA') && (
        <AnimSuma num1={numero1} num2={numero2} pasoActual={pasoActual} totalPasos={totalPasos} />
      )}
      {(operacion === 'RESTA') && (
        <AnimResta num1={numero1} num2={numero2} pasoActual={pasoActual} totalPasos={totalPasos} />
      )}
      {operacion === 'MULTIPLICACION' && (
        <AnimMultiplicacion num1={numero1} num2={numero2} pasoActual={pasoActual} totalPasos={totalPasos} />
      )}
      {operacion === 'DIVISION' && (
        <AnimDivision num1={numero1} num2={numero2} pasoActual={pasoActual} totalPasos={totalPasos} />
      )}
    </div>
  );
}
