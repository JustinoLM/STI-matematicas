import { useEffect } from 'react';
import { useProblemInput } from '@/hooks';

/** Ancho de N celdas + gaps como valor CSS rem — escala con cualquier font-size raíz */
const cw = (n: number) => `calc(${n} * 2.75rem)`;
import { DigitRow, OperatorSymbol, HorizontalLine, CarrySpaces, BorrowSpaces } from './atoms';

interface SumaRestaGridProps {
  operacion: 'SUMA' | 'RESTA';
  numero1: number;
  numero2: number;
  resultado: number;
  onAnswerChange: (answer: string) => void;
  showFeedback: boolean;
  clearIncorrectTrigger?: number;
}

/**
 * Grid especializado para operaciones de suma y resta
 * Con soporte de decimales, llevadas y alineación automática
 */
export function SumaRestaGrid({
  operacion,
  numero1,
  numero2,
  resultado: _resultado,
  onAnswerChange,
  showFeedback,
  clearIncorrectTrigger,
}: SumaRestaGridProps) {
  // Alinear decimales
  const alinearDecimales = (num1: number, num2: number) => {
    const str1 = num1.toString();
    const str2 = num2.toString();

    const decimal1 = str1.includes('.') ? str1.split('.')[1].length : 0;
    const decimal2 = str2.includes('.') ? str2.split('.')[1].length : 0;
    const maxDecimales = Math.max(decimal1, decimal2);

    const aligned1 =
      decimal1 < maxDecimales
        ? decimal1 === 0
          ? str1 + '.' + '0'.repeat(maxDecimales)
          : str1 + '0'.repeat(maxDecimales - decimal1)
        : str1;
    const aligned2 =
      decimal2 < maxDecimales
        ? decimal2 === 0
          ? str2 + '.' + '0'.repeat(maxDecimales)
          : str2 + '0'.repeat(maxDecimales - decimal2)
        : str2;

    return { aligned1, aligned2 };
  };

  const { aligned1, aligned2 } = alinearDecimales(numero1, numero2);

  // Calcular el resultado real para determinar cuántas casillas mostrar.
  // El prop `resultado` llega como 0 desde PracticePage, así que lo calculamos aquí.
  const calcularResultadoStr = () => {
    const decimales = aligned1.includes('.')
      ? aligned1.split('.')[1].length
      : 0;
    const r = operacion === 'SUMA' ? numero1 + numero2 : numero1 - numero2;
    return decimales > 0 ? r.toFixed(decimales) : Math.round(r).toString();
  };

  const resultadoStr = calcularResultadoStr();
  const maxLength = Math.max(aligned1.length, aligned2.length, resultadoStr.length);

  // Construir valores esperados para validación
  const expectedValues: { [key: string]: string } = {};
  resultadoStr.split('').forEach((char, index) => {
    expectedValues[`resultado-${index}`] = char;
  });

  const {
    digitosRespuesta,
    focusedKey,
    inputRefs,
    setFocusedKey,
    handleDigitChange,
  } = useProblemInput({
    showFeedback,
    direction: 'right-to-left',
    problemKey: `${numero1}-${numero2}-${operacion}`,
    clearIncorrectTrigger,
    expectedValues,
  });

  // Notificar cambios - SOLO resultado final
  useEffect(() => {
    const resultadoFinal = Object.keys(digitosRespuesta)
      .filter(key => key.startsWith('resultado-'))
      .sort((a, b) => parseInt(a.split('-')[1]) - parseInt(b.split('-')[1]))
      .map(key => digitosRespuesta[key])
      .join('');
    onAnswerChange(resultadoFinal);
  }, [digitosRespuesta, onAnswerChange]);

  return (
    <div className="flex flex-col items-end gap-2 font-mono text-xl">
      {/* Espacio para llevadas o prestadas según la operación */}
      {operacion === 'SUMA' ? (
        <CarrySpaces count={maxLength} width={cw(maxLength)} />
      ) : (
        <BorrowSpaces count={maxLength} width={cw(maxLength)} />
      )}

      {/* Primer número */}
      <div className="flex gap-1 justify-end" style={{ width: cw(maxLength) }}>
        {aligned1.split('').map((char, i) => (
          <span key={`num1-${i}`} className="w-10 h-10 flex items-center justify-center font-bold">
            {char}
          </span>
        ))}
      </div>

      {/* Operador + segundo número */}
      <div className="flex items-center gap-2 justify-end">
        <OperatorSymbol operacion={operacion} />
        <div className="flex gap-1">
          {aligned2.split('').map((char, i) => (
            <span key={`num2-${i}`} className="w-10 h-10 flex items-center justify-center font-bold">
              {char}
            </span>
          ))}
        </div>
      </div>

      {/* Línea separadora */}
      <HorizontalLine width={cw(maxLength)} />

      {/* Resultado con inputs */}
      <DigitRow
        expectedValue={resultadoStr}
        digitosRespuesta={digitosRespuesta}
        keyPrefix="resultado"
        inputRefs={inputRefs}
        focusedKey={focusedKey}
        showFeedback={showFeedback}
        onDigitChange={handleDigitChange}
        onFocus={setFocusedKey}
        onBlur={() => setFocusedKey(null)}
        direction="right-to-left"
      />
    </div>
  );
}
