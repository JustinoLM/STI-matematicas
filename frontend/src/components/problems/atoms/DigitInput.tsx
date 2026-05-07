import { forwardRef } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface DigitInputProps {
  value: string;
  expectedValue: string;
  onChange: (value: string) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  showFeedback?: boolean;
  isFocused?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Input individual para un dígito matemático
 * Con feedback visual automático (verde/rojo) y estados de focus
 */
export const DigitInput = forwardRef<HTMLInputElement, DigitInputProps>(
  (
    {
      value,
      expectedValue,
      onChange,
      onFocus,
      onBlur,
      onKeyDown,
      disabled = false,
      showFeedback = false,
      isFocused = false,
      placeholder = '?',
      className,
    },
    ref
  ) => {
    const isCorrect = value === expectedValue;

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      // Permitir navegación y borrado
      if (onKeyDown) {
        onKeyDown(e);
      }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value;
      // Si el nuevo valor está vacío, permitir el borrado
      if (newValue === '') {
        onChange('');
        return;
      }
      // Solo tomar el último carácter ingresado
      const lastChar = newValue.slice(-1);
      onChange(lastChar);
    };

    return (
      <Input
        ref={ref}
        type="text"
        inputMode="none"
        maxLength={1}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
        disabled={disabled}
        className={cn(
          'w-10 h-10 text-center text-base font-bold p-0 transition-all',
          showFeedback
            ? isCorrect
              ? 'bg-green-100 border-green-500 text-green-800'
              : 'bg-red-100 border-red-500 text-red-800'
            : isFocused
              ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-300'
              : 'bg-white',
          className
        )}
        placeholder={placeholder}
      />
    );
  }
);

DigitInput.displayName = 'DigitInput';
