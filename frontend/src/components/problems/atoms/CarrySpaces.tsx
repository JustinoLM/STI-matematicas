import { useState } from 'react';

interface CarrySpacesProps {
  count: number;
  width: number | string;
}

/**
 * Espacios para que los estudiantes anoten sus llevadas
 * Sin validación - solo para ayuda visual
 */
export function CarrySpaces({ count, width }: CarrySpacesProps) {
  const [carries, setCarries] = useState<{ [key: number]: string }>({});

  const handleChange = (index: number, value: string) => {
    // Permitir vacío o un solo dígito
    if (value === '' || (value.length === 1 && /^[0-9]$/.test(value))) {
      setCarries(prev => ({
        ...prev,
        [index]: value,
      }));
    }
  };

  const handleKeyDown = (index: number) => (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Navegación con flechas horizontales
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      if (index > 0) {
        const prevInput = document.getElementById(`carry-input-${index - 1}`);
        prevInput?.focus();
      }
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      if (index < count - 1) {
        const nextInput = document.getElementById(`carry-input-${index + 1}`);
        nextInput?.focus();
      }
    }

    // Backspace navigation
    if (e.key === 'Backspace') {
      const currentValue = carries[index] || '';

      // Si el input actual está vacío y presionan backspace, ir al anterior
      if (currentValue === '' && index > 0) {
        e.preventDefault();
        const prevInput = document.getElementById(`carry-input-${index - 1}`);
        if (prevInput) {
          prevInput.focus();
          // Limpiar el input anterior
          setCarries(prev => ({
            ...prev,
            [index - 1]: '',
          }));
        }
      }
    }
  };

  return (
    <div className="flex flex-col items-end">
      <div className="text-xs text-gray-400 mb-1 font-sans">Espacio para llevadas</div>
      <div className="flex gap-1 justify-end" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
        {Array.from({ length: count }).map((_, i) => (
          <input
            key={`carry-${i}`}
            id={`carry-input-${i}`}
            type="text"
            inputMode="numeric"
            value={carries[i] || ''}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={handleKeyDown(i)}
            className="w-10 h-10 text-center text-base text-gray-500 border border-gray-200 rounded outline-none focus:border-blue-300 focus:text-gray-700 font-mono bg-gray-50 focus:bg-white transition-colors"
            placeholder=""
            maxLength={1}
          />
        ))}
      </div>
    </div>
  );
}
