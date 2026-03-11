/**
 * Grid de problema en modo demostración (solo visual, sin inputs).
 *
 * Muestra la operación con el resultado revelándose progresivamente
 * de derecha a izquierda, sincronizado con el paso activo del modal.
 *
 * Cada celda del resultado empieza vacía (con borde gris) y se va
 * rellenando a medida que el estudiante avanza por los pasos.
 */

import type { Operacion } from '@/types';

// ─── Tipos ────────────────────────────────────────────────────────────────────

interface AnimacionGridProps {
  operacion: Operacion;
  numero1: number;
  numero2: number;
  /** Índice del paso activo (0-based) */
  pasoActual: number;
  /** Total de pasos */
  totalPasos: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function calcResultado(operacion: Operacion, num1: number, num2: number): string {
  const s1 = String(num1);
  const s2 = String(num2);
  const dec1 = s1.includes('.') ? s1.split('.')[1].length : 0;
  const dec2 = s2.includes('.') ? s2.split('.')[1].length : 0;
  const maxDec = Math.max(dec1, dec2);

  switch (operacion) {
    case 'SUMA': {
      const r = parseFloat((num1 + num2).toFixed(maxDec + 1));
      return maxDec === 0 ? r.toFixed(0) : r.toFixed(maxDec);
    }
    case 'RESTA': {
      const r = parseFloat((num1 - num2).toFixed(maxDec + 1));
      return maxDec === 0 ? r.toFixed(0) : r.toFixed(maxDec);
    }
    case 'MULTIPLICACION': {
      const totalDec = dec1 + dec2;
      const r = parseFloat((num1 * num2).toFixed(totalDec + 1));
      return totalDec === 0 ? r.toFixed(0) : r.toFixed(totalDec);
    }
    case 'DIVISION': {
      const r = parseFloat((num1 / num2).toFixed(2));
      return r % 1 === 0 ? r.toFixed(0) : r.toFixed(2);
    }
  }
}

function alignDecimals(num1: number, num2: number): { a1: string; a2: string } {
  const s1 = String(num1);
  const s2 = String(num2);
  const dec1 = s1.includes('.') ? s1.split('.')[1].length : 0;
  const dec2 = s2.includes('.') ? s2.split('.')[1].length : 0;
  const maxDec = Math.max(dec1, dec2);

  const pad = (s: string, dec: number) => {
    if (dec >= maxDec) return s;
    return dec === 0 ? s + '.' + '0'.repeat(maxDec) : s + '0'.repeat(maxDec - dec);
  };

  return { a1: pad(s1, dec1), a2: pad(s2, dec2) };
}

// ─── Celda de resultado (revelable) ───────────────────────────────────────────

interface ResultCellProps {
  char: string;
  revealed: boolean;
  isComplete: boolean;
}

function ResultCell({ char, revealed, isComplete }: ResultCellProps) {
  if (char === '.') {
    return (
      <span className="w-4 h-10 flex items-center justify-end pb-0.5 font-bold text-2xl text-gray-700">
        .
      </span>
    );
  }
  return (
    <span
      className={[
        'w-10 h-10 flex items-center justify-center font-bold text-2xl border-2 rounded transition-all duration-500',
        revealed && isComplete
          ? 'bg-green-100 text-green-700 border-green-400 scale-105'
          : revealed
          ? 'bg-blue-50 text-blue-800 border-blue-300'
          : 'bg-gray-50 text-transparent border-gray-200',
      ].join(' ')}
    >
      {revealed ? char : ''}
    </span>
  );
}

// ─── Fila de resultado con revelación progresiva ──────────────────────────────

interface DemoResultRowProps {
  value: string;
  revealedCount: number;
  isComplete: boolean;
}

function DemoResultRow({ value, revealedCount, isComplete }: DemoResultRowProps) {
  const chars = value.split('');
  const nonDecTotal = chars.filter((c) => c !== '.').length;
  let digitRank = -1;

  return (
    <div className="flex gap-1 items-center">
      {chars.map((char, i) => {
        if (char === '.') {
          return <ResultCell key={i} char="." revealed={true} isComplete={false} />;
        }
        digitRank++;
        // Reveal from right to left: rank 0 is leftmost digit
        const revealed = digitRank >= nonDecTotal - revealedCount;
        return (
          <ResultCell
            key={i}
            char={char}
            revealed={revealed}
            isComplete={isComplete && revealed}
          />
        );
      })}
    </div>
  );
}

// ─── Celda estática (número del problema) ────────────────────────────────────

function StaticChar({ char }: { char: string }) {
  const isDecimal = char === '.';
  return (
    <span
      className={[
        'flex items-center justify-center font-bold text-2xl text-gray-800',
        isDecimal ? 'w-4 h-10' : 'w-10 h-10',
      ].join(' ')}
    >
      {char}
    </span>
  );
}

function StaticNumber({ value }: { value: string }) {
  return (
    <div className="flex gap-1 items-center">
      {value.split('').map((char, i) => (
        <StaticChar key={i} char={char} />
      ))}
    </div>
  );
}

function DemoLine({ width }: { width: number }) {
  return <div className="border-t-2 border-gray-600 mt-1" style={{ width: `${width}px` }} />;
}

// ─── Grid SUMA / RESTA ────────────────────────────────────────────────────────

interface DemoSumaRestaProps {
  operacion: 'SUMA' | 'RESTA';
  num1: number;
  num2: number;
  revealedCount: number;
  isComplete: boolean;
}

function DemoSumaResta({ operacion, num1, num2, revealedCount, isComplete }: DemoSumaRestaProps) {
  const { a1, a2 } = alignDecimals(num1, num2);
  const resultadoStr = calcResultado(operacion, num1, num2);
  const charWidth = 44; // w-10 = 2.5rem ≈ 40px + gap-1 ~= 44px
  const maxLen = Math.max(a1.length, a2.length, resultadoStr.length);
  const lineWidth = maxLen * charWidth;
  const simbolo = operacion === 'SUMA' ? '+' : '−';

  return (
    <div className="flex flex-col items-end gap-2 font-mono">
      {/* Número 1 */}
      <StaticNumber value={a1} />

      {/* Símbolo + número 2 */}
      <div className="flex items-center gap-2">
        <span className="font-bold text-2xl text-gray-500 w-6 text-right">{simbolo}</span>
        <StaticNumber value={a2} />
      </div>

      {/* Línea */}
      <DemoLine width={lineWidth} />

      {/* Resultado */}
      <DemoResultRow value={resultadoStr} revealedCount={revealedCount} isComplete={isComplete} />
    </div>
  );
}

// ─── Grid MULTIPLICACIÓN ──────────────────────────────────────────────────────

interface DemoMultiplicacionProps {
  num1: number;
  num2: number;
  revealedCount: number;
  isComplete: boolean;
}

function DemoMultiplicacion({ num1, num2, revealedCount, isComplete }: DemoMultiplicacionProps) {
  const resultadoStr = calcResultado('MULTIPLICACION', num1, num2);
  const n1str = String(num1);
  const n2str = String(num2);
  const charWidth = 44;
  const maxLen = Math.max(n1str.length, n2str.length, resultadoStr.length);
  const lineWidth = maxLen * charWidth;

  return (
    <div className="flex flex-col items-end gap-2 font-mono">
      <StaticNumber value={n1str} />
      <div className="flex items-center gap-2">
        <span className="font-bold text-2xl text-gray-500 w-6 text-right">×</span>
        <StaticNumber value={n2str} />
      </div>
      <DemoLine width={lineWidth} />
      <DemoResultRow value={resultadoStr} revealedCount={revealedCount} isComplete={isComplete} />
    </div>
  );
}

// ─── Grid DIVISIÓN ────────────────────────────────────────────────────────────

interface DemoDivisionProps {
  num1: number;
  num2: number;
  revealedCount: number;
  isComplete: boolean;
}

function DemoDivision({ num1, num2, revealedCount, isComplete }: DemoDivisionProps) {
  const resultadoStr = calcResultado('DIVISION', num1, num2);
  const n1str = String(num1);
  const n2str = String(num2);

  return (
    <div className="flex items-center gap-2 font-mono flex-wrap justify-center">
      <StaticNumber value={n1str} />
      <span className="font-bold text-2xl text-gray-500">÷</span>
      <StaticNumber value={n2str} />
      <span className="font-bold text-2xl text-gray-500">=</span>
      <DemoResultRow value={resultadoStr} revealedCount={revealedCount} isComplete={isComplete} />
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function AnimacionGrid({
  operacion,
  numero1,
  numero2,
  pasoActual,
  totalPasos,
}: AnimacionGridProps) {
  const resultado = calcResultado(operacion, numero1, numero2);
  const totalDigits = resultado.replace('.', '').length;

  // Paso 0 → 0 dígitos; último paso → todos; intermedios → proporcional
  const revealedCount =
    pasoActual === 0
      ? 0
      : pasoActual >= totalPasos - 1
      ? totalDigits
      : Math.ceil((pasoActual / (totalPasos - 1)) * totalDigits);

  const isComplete = pasoActual >= totalPasos - 1;

  return (
    <div className="bg-white rounded-xl border-2 border-gray-100 p-6 flex items-center justify-center min-h-[120px]">
      {(operacion === 'SUMA' || operacion === 'RESTA') && (
        <DemoSumaResta
          operacion={operacion}
          num1={numero1}
          num2={numero2}
          revealedCount={revealedCount}
          isComplete={isComplete}
        />
      )}
      {operacion === 'MULTIPLICACION' && (
        <DemoMultiplicacion
          num1={numero1}
          num2={numero2}
          revealedCount={revealedCount}
          isComplete={isComplete}
        />
      )}
      {operacion === 'DIVISION' && (
        <DemoDivision
          num1={numero1}
          num2={numero2}
          revealedCount={revealedCount}
          isComplete={isComplete}
        />
      )}
    </div>
  );
}
