import { useState } from 'react';

interface BorrowSpacesProps {
  count: number;
  width: number | string;
}

/**
 * Espacios para que los estudiantes anoten sus "prestadas" en restas
 * Permite hasta 2 dígitos por input (ej: 0 → 10)
 */
export function BorrowSpaces({ count, width }: BorrowSpacesProps) {
  const [borrows, setBorrows] = useState<{ [key: number]: string }>({});

  const handleChange = (index: number, value: string) => {
    // Permitir vacío o hasta 2 dígitos numéricos
    if (value === '' || (value.length <= 2 && /^[0-9]{1,2}$/.test(value))) {
      setBorrows(prev => ({
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
        const prevInput = document.getElementById(`borrow-input-${index - 1}`);
        prevInput?.focus();
      }
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      if (index < count - 1) {
        const nextInput = document.getElementById(`borrow-input-${index + 1}`);
        nextInput?.focus();
      }
    }

    // Backspace navigation
    if (e.key === 'Backspace') {
      const currentValue = borrows[index] || '';

      // Si el input actual está vacío y presionan backspace, ir al anterior
      if (currentValue === '' && index > 0) {
        e.preventDefault();
        const prevInput = document.getElementById(`borrow-input-${index - 1}`);
        if (prevInput) {
          prevInput.focus();
          // Limpiar el input anterior
          setBorrows(prev => ({
            ...prev,
            [index - 1]: '',
          }));
        }
      }
    }
  };

  return (
    <div className="flex flex-col items-end">
      <div className="text-xs text-gray-400 mb-1 font-sans">Espacio para prestadas</div>
      <div className="flex gap-1 justify-end" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
        {Array.from({ length: count }).map((_, i) => (
          <input
            key={`borrow-${i}`}
            id={`borrow-input-${i}`}
            type="text"
            inputMode="none"
            value={borrows[i] || ''}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={handleKeyDown(i)}
            className="w-10 h-10 text-center text-sm text-purple-600 border border-purple-200 rounded outline-none focus:border-purple-400 focus:text-purple-800 font-mono bg-purple-50 focus:bg-white transition-colors"
            placeholder=""
            maxLength={2}
          />
        ))}
      </div>
    </div>
  );
}
