import { useEffect } from 'react';
import { useProblemInput, useMultiplicationCalculator } from '@/hooks';

/** Ancho de N celdas + gaps como valor CSS rem */
const cw = (n: number) => `calc(${n} * 2.75rem)`;
import { DigitRow, OperatorSymbol, HorizontalLine, CarrySpaces } from './atoms';

interface MultiplicacionGridProps {
  numero1: number;
  numero2: number;
  onAnswerChange: (answer: string) => void;
  showFeedback: boolean;
  clearIncorrectTrigger?: number;
}

/**
 * Grid especializado para multiplicación
 * Con productos parciales, alineación y soporte de decimales
 */
export function MultiplicacionGrid({
  numero1,
  numero2,
  onAnswerChange,
  showFeedback,
  clearIncorrectTrigger,
}: MultiplicacionGridProps) {
  const { multiplicandoStr, productosParciales, resultadoStr } =
    useMultiplicationCalculator(numero1, numero2);

  const multiplicandoDisplay = numero1.toString();
  const multiplicadorDisplay = numero2.toString();

  // Construir valores esperados para validación (resultado + productos parciales)
  const expectedValues: { [key: string]: string } = {};

  // Resultado final
  resultadoStr.split('').forEach((char, index) => {
    expectedValues[`resultado-${index}`] = char;
  });

  // Productos parciales
  productosParciales.forEach((parcial, idx) => {
    parcial.valorStr.split('').forEach((char, charIdx) => {
      expectedValues[`parcial-${idx}-${charIdx}`] = char;
    });
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
    problemKey: `${numero1}-${numero2}-MULTIPLICACION`,
    clearIncorrectTrigger,
    expectedValues,
  });



  // Notificar cambios - SOLO resultado final, no productos parciales
  useEffect(() => {
    const resultadoFinal = Object.keys(digitosRespuesta)
      .filter(key => key.startsWith('resultado-'))
      .sort()
      .map(key => digitosRespuesta[key])
      .join('');

    onAnswerChange(resultadoFinal);
  }, [digitosRespuesta, onAnswerChange]);

  return (
    <div className="flex flex-col items-end gap-2 font-mono text-xl">
      {/* Espacio para llevadas arriba del multiplicando */}
      <CarrySpaces count={resultadoStr.length} width={cw(resultadoStr.length)} />

      {/* Multiplicando */}
      <div className="flex gap-1 justify-end">
        {multiplicandoDisplay.split('').map((digit, i) => (
          <span key={`mult1-${i}`} className="w-10 h-10 flex items-center justify-center font-bold">
            {digit}
          </span>
        ))}
      </div>

      {/* Operador + multiplicador */}
      <div className="flex items-center gap-2 justify-end">
        <OperatorSymbol operacion="MULTIPLICACION" />
        <div className="flex gap-1">
          {multiplicadorDisplay.split('').map((digit, i) => (
            <span key={`mult2-${i}`} className="w-10 h-10 flex items-center justify-center font-bold">
              {digit}
            </span>
          ))}
        </div>
      </div>

      {/* Línea separadora */}
      <HorizontalLine width={cw(multiplicandoStr.length)} />

      {/* Productos parciales */}
      <div className="flex flex-col items-end space-y-1">
        {productosParciales.map((parcial, idx) => (
          <DigitRow
            key={`parcial-${idx}`}
            expectedValue={parcial.valorStr}
            digitosRespuesta={digitosRespuesta}
            keyPrefix={`parcial-${idx}`}
            inputRefs={inputRefs}
            focusedKey={focusedKey}
            showFeedback={showFeedback}
            onDigitChange={handleDigitChange}
            onFocus={setFocusedKey}
            onBlur={() => setFocusedKey(null)}
            direction="right-to-left"
            offsetCells={parcial.espacios}
          />
        ))}
      </div>

      {/* Línea separadora final */}
      <HorizontalLine width={cw(resultadoStr.length + Math.max(...productosParciales.map(p => p.espacios)))} />

      {/* Resultado final */}
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
