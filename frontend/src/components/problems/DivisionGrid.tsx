import { useEffect } from 'react';
import { useProblemInput, useDivisionCalculator } from '@/hooks';
import { DigitRow, OperatorSymbol, HorizontalLine } from './atoms';

/** Ancho de N celdas + gaps como valor CSS rem */
const cw = (n: number) => `calc(${n} * 2.75rem)`;

interface DivisionGridProps {
  numero1: number;
  numero2: number;
  resultado: number;
  onAnswerChange: (answer: string) => void;
  showFeedback: boolean;
  clearIncorrectTrigger?: number;
}

export function DivisionGrid({
  numero1,
  numero2,
  resultado,
  onAnswerChange,
  showFeedback,
  clearIncorrectTrigger,
}: DivisionGridProps) {
  const {
    cocienteStr = '',
    pasos = [],
    requiereNormalizacion = false,
    dividendoNormalizadoStr = '',
    divisorNormalizadoStr = '',
  } = useDivisionCalculator(numero1, numero2, resultado);

  // Convertir los números originales a strings para display
  const dividendoStr = numero1.toString();
  const divisorStr = numero2.toString();

  // Determinar si es método vertical (dividendo con decimales, divisor sin decimales)
  const esMetodoVertical = dividendoStr.includes('.') && !divisorStr.includes('.');

  // Construir valores esperados para validación
  const expectedValues: { [key: string]: string } = {};

  // Cociente
  cocienteStr.split('').forEach((char, index) => {
    expectedValues[`cociente-${index}`] = char;
  });

  // Normalización del dividendo (método vertical o normalización completa)
  if (requiereNormalizacion || esMetodoVertical) {
    dividendoNormalizadoStr.split('').forEach((char: string, index: number) => {
      expectedValues[`dividendo-norm-${index}`] = char;
    });
  }

  // Normalización del divisor (solo si requiere normalización completa)
  if (requiereNormalizacion) {
    divisorNormalizadoStr.split('').forEach((char: string, index: number) => {
      expectedValues[`divisor-norm-${index}`] = char;
    });
  }

  // Pasos intermedios (productos, dividendos parciales y residuos)
  pasos.forEach((paso, idx) => {
    // Dividendo parcial — solo desde el segundo paso en adelante
    if (idx > 0 && paso.dividendoParcialStr) {
      paso.dividendoParcialStr.split('').forEach((char: string, charIdx: number) => {
        expectedValues[`paso-${idx}-dividendo-parcial-${charIdx}`] = char;
      });
    }

    // Producto (lo que se resta)
    paso.productoStr.split('').forEach((char: string, charIdx: number) => {
      expectedValues[`paso-${idx}-producto-${charIdx}`] = char;
    });

    // Residuo (solo el último paso)
    if (idx === pasos.length - 1) {
      paso.residuoStr.split('').forEach((char: string, charIdx: number) => {
        expectedValues[`paso-${idx}-residuo-${charIdx}`] = char;
      });
    }
  });

  const {
    digitosRespuesta,
    focusedKey,
    inputRefs,
    setFocusedKey,
    handleDigitChange,
  } = useProblemInput({
    showFeedback,
    direction: 'left-to-right',
    problemKey: `${numero1}-${numero2}-DIVISION`,
    clearIncorrectTrigger,
    expectedValues,
  });

  useEffect(() => {
    const cocienteFinal = Object.keys(digitosRespuesta)
      .filter(k => k.startsWith('cociente-'))
      .sort()
      .map(k => digitosRespuesta[k])
      .join('');

    onAnswerChange(cocienteFinal);
  }, [digitosRespuesta, onAnswerChange]);

  return (
    <div className="flex flex-col items-start gap-2 font-mono text-xl">
      {/* División Original */}
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {dividendoStr.split('').map((d, i) => (
            <span key={i} className="w-10 h-10 flex items-center justify-center font-bold">
              {d}
            </span>
          ))}
        </div>

        <OperatorSymbol operacion="DIVISION" />

        <div className="flex gap-1">
          {divisorStr.split('').map((d, i) => (
            <span key={i} className="w-10 h-10 flex items-center justify-center font-bold">
              {d}
            </span>
          ))}
        </div>

        <span className="font-bold">=</span>

        <DigitRow
          expectedValue={cocienteStr}
          digitosRespuesta={digitosRespuesta}
          keyPrefix="cociente"
          inputRefs={inputRefs}
          focusedKey={focusedKey}
          showFeedback={showFeedback}
          onDigitChange={handleDigitChange}
          onFocus={setFocusedKey}
          onBlur={() => setFocusedKey(null)}
        />
      </div>

      {/* Normalización para método vertical (dividendo con decimales) */}
      {esMetodoVertical && (
        <div className="space-y-1 mt-2">
          <div className="text-sm text-gray-600 font-sans">
            Normalizamos el dividendo (×{Math.pow(10, dividendoStr.includes('.') ? dividendoStr.split('.')[1].length : 0)}):
          </div>

          <DigitRow
            expectedValue={dividendoNormalizadoStr}
            digitosRespuesta={digitosRespuesta}
            keyPrefix="dividendo-norm"
            inputRefs={inputRefs}
            focusedKey={focusedKey}
            showFeedback={showFeedback}
            onDigitChange={handleDigitChange}
            onFocus={setFocusedKey}
            onBlur={() => setFocusedKey(null)}
          />

          <HorizontalLine width={cw(dividendoNormalizadoStr.length)} />
        </div>
      )}

      {/* Normalización (solo si el divisor tiene decimales) */}
      {requiereNormalizacion && (
        <div className="space-y-1 mt-2">
          <div className="text-sm text-gray-600 font-sans">
            Normalizamos ambos números (×{Math.pow(10, Math.max(
              dividendoStr.includes('.') ? dividendoStr.split('.')[1].length : 0,
              divisorStr.includes('.') ? divisorStr.split('.')[1].length : 0
            ))}):
          </div>

          <div className="flex items-center gap-2">
            <DigitRow
              expectedValue={dividendoNormalizadoStr}
              digitosRespuesta={digitosRespuesta}
              keyPrefix="dividendo-norm"
              inputRefs={inputRefs}
              focusedKey={focusedKey}
              showFeedback={showFeedback}
              onDigitChange={handleDigitChange}
              onFocus={setFocusedKey}
              onBlur={() => setFocusedKey(null)}
            />

            <OperatorSymbol operacion="DIVISION" />

            <DigitRow
              expectedValue={divisorNormalizadoStr}
              digitosRespuesta={digitosRespuesta}
              keyPrefix="divisor-norm"
              inputRefs={inputRefs}
              focusedKey={focusedKey}
              showFeedback={showFeedback}
              onDigitChange={handleDigitChange}
              onFocus={setFocusedKey}
              onBlur={() => setFocusedKey(null)}
            />
          </div>
        </div>
      )}

      {!requiereNormalizacion && !esMetodoVertical && (
        <HorizontalLine width={cw(dividendoStr.length)} />
      )}

      {/* Pasos */}
      <div className="space-y-1">
        {pasos.map((paso, idx: number) => (
          <div key={idx} className="space-y-1">
            {/* Dividendo parcial — solo desde el segundo paso en adelante */}
            {idx > 0 && paso.dividendoParcialStr && (
              <DigitRow
                expectedValue={paso.dividendoParcialStr}
                digitosRespuesta={digitosRespuesta}
                keyPrefix={`paso-${idx}-dividendo-parcial`}
                inputRefs={inputRefs}
                focusedKey={focusedKey}
                showFeedback={showFeedback}
                onDigitChange={handleDigitChange}
                onFocus={setFocusedKey}
                onBlur={() => setFocusedKey(null)}
                paddingLeft={cw(paso.espaciosDividendoParcial ?? 0)}
              />
            )}

            <DigitRow
              expectedValue={paso.productoStr ?? ''}
              digitosRespuesta={digitosRespuesta}
              keyPrefix={`paso-${idx}-producto`}
              inputRefs={inputRefs}
              focusedKey={focusedKey}
              showFeedback={showFeedback}
              onDigitChange={handleDigitChange}
              onFocus={setFocusedKey}
              onBlur={() => setFocusedKey(null)}
              paddingLeft={cw(paso.espaciosProducto ?? 0)}
            />

            <HorizontalLine
              width={cw(paso.productoStr?.length ?? 0)}
              marginLeft={cw(paso.espaciosProducto ?? 0)}
            />

            {/* Mostrar residuo solo si es el último paso */}
            {idx === pasos.length - 1 && (
              <DigitRow
                expectedValue={paso.residuoStr ?? ''}
                digitosRespuesta={digitosRespuesta}
                keyPrefix={`paso-${idx}-residuo`}
                inputRefs={inputRefs}
                focusedKey={focusedKey}
                showFeedback={showFeedback}
                onDigitChange={handleDigitChange}
                onFocus={setFocusedKey}
                onBlur={() => setFocusedKey(null)}
                paddingLeft={cw(paso.espaciosResiduo ?? 0)}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
