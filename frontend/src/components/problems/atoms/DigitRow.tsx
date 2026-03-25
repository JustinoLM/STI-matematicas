import { DigitInput } from './DigitInput';

interface DigitRowProps {
  expectedValue: string; // El string completo esperado (ej: "123.45")
  digitosRespuesta: { [key: string]: string };
  keyPrefix: string; // Prefijo para las keys (ej: "resultado")
  inputRefs: React.MutableRefObject<{ [key: string]: HTMLInputElement | null }>;
  focusedKey: string | null;
  showFeedback: boolean;
  onDigitChange: (key: string, value: string, nextKey?: string) => void;
  onFocus: (key: string) => void;
  onBlur: () => void;
  direction?: 'left-to-right' | 'right-to-left';
  paddingLeft?: number | string; // Espacios a la izquierda (división): px o CSS string
  offsetCells?: number; // Número de celdas vacías a la derecha (multiplicación)
  readOnly?: boolean;
}

/**
 * Componente que renderiza una fila completa de inputs para dígitos
 * Maneja automáticamente puntos decimales y auto-focus
 */
export function DigitRow({
  expectedValue,
  digitosRespuesta,
  keyPrefix,
  inputRefs,
  focusedKey,
  showFeedback,
  onDigitChange,
  onFocus,
  onBlur,
  direction = 'left-to-right',
  paddingLeft = 0,
  offsetCells = 0,
}: DigitRowProps) {
  const chars = expectedValue.split('');

  const getNextKey = (currentIndex: number): string | undefined => {
    if (direction === 'left-to-right') {
      const nextIndex = currentIndex + 1;
      return nextIndex < chars.length ? `${keyPrefix}-${nextIndex}` : undefined;
    } else {
      // right-to-left
      const prevIndex = currentIndex - 1;
      return prevIndex >= 0 ? `${keyPrefix}-${prevIndex}` : undefined;
    }
  };

  const getPrevKey = (currentIndex: number): string | undefined => {
    if (direction === 'left-to-right') {
      const prevIndex = currentIndex - 1;
      return prevIndex >= 0 ? `${keyPrefix}-${prevIndex}` : undefined;
    } else {
      // right-to-left
      const nextIndex = currentIndex + 1;
      return nextIndex < chars.length ? `${keyPrefix}-${nextIndex}` : undefined;
    }
  };

  const handleKeyDown = (index: number, key: string) => (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Navegación con flechas
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();

      if (e.key === 'ArrowLeft') {
        // Ir al input anterior (izquierda)
        const prevIndex = index - 1;
        if (prevIndex >= 0) {
          const prevKey = `${keyPrefix}-${prevIndex}`;
          inputRefs.current[prevKey]?.focus();
        }
      } else if (e.key === 'ArrowRight') {
        // Ir al siguiente input (derecha)
        const nextIndex = index + 1;
        if (nextIndex < chars.length) {
          const nextKey = `${keyPrefix}-${nextIndex}`;
          inputRefs.current[nextKey]?.focus();
        }
      }
    }

    // Backspace navigation
    if (e.key === 'Backspace' || e.key === 'Delete') {
      const currentValue = digitosRespuesta[key] || '';

      // Si el input actual está vacío y presionan backspace, ir al anterior
      if (currentValue === '' && e.key === 'Backspace') {
        e.preventDefault();
        const prevKey = getPrevKey(index);
        if (prevKey && inputRefs.current[prevKey]) {
          inputRefs.current[prevKey]?.focus();
          // Limpiar el input anterior
          onDigitChange(prevKey, '');
        }
      }
    }
  };

  return (
    <div className="flex gap-1" style={{ paddingLeft: paddingLeft === undefined ? undefined : typeof paddingLeft === 'number' ? `${paddingLeft}px` : paddingLeft }}>
      {chars.map((char, index) => {
        const key = `${keyPrefix}-${index}`;
        const nextKey = getNextKey(index);
        const value = digitosRespuesta[key] || '';
        const isFocused = focusedKey === key;

        // Espacio — celda vacía no-editable (marcador de posición del decimal en productos parciales)
        if (char === ' ') {
          return <div key={key} className="w-10 h-10" />;
        }

        // Punto decimal - editable
        if (char === '.') {
          return (
            <DigitInput
              key={key}
              ref={(el) => (inputRefs.current[key] = el)}
              value={value}
              expectedValue="."
              onChange={(val) => onDigitChange(key, val, nextKey)}
              onFocus={() => onFocus(key)}
              onBlur={onBlur}
              onKeyDown={handleKeyDown(index, key)}
              showFeedback={showFeedback}
              isFocused={isFocused}
            />
          );
        }

        // Dígito normal
        return (
          <DigitInput
            key={key}
            ref={(el) => (inputRefs.current[key] = el)}
            value={value}
            expectedValue={char}
            onChange={(val) => onDigitChange(key, val, nextKey)}
            onFocus={() => onFocus(key)}
            onBlur={onBlur}
            onKeyDown={handleKeyDown(index, key)}
            showFeedback={showFeedback}
            isFocused={isFocused}
          />
        );
      })}

      {/* Celdas vacías a la DERECHA (para productos parciales en multiplicación) */}
      {offsetCells > 0 &&
        Array.from({ length: offsetCells }).map((_, i) => (
          <div key={`offset-right-${i}`} className="w-10 h-10" />
        ))}
    </div>
  );
}
