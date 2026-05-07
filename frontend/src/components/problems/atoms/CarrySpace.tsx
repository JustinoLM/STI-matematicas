import { forwardRef } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface CarrySpaceProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Input pequeño para números de llevada (carry)
 * Usado en suma, resta y multiplicación
 */
export const CarrySpace = forwardRef<HTMLInputElement, CarrySpaceProps>(
  ({ value, onChange, disabled = false, className }, ref) => {
    return (
      <Input
        ref={ref}
        type="text"
        inputMode="none"
        maxLength={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={cn(
          'w-8 h-8 text-center text-xs font-semibold p-0',
          'bg-gray-50 border-gray-300 text-gray-600',
          'focus:ring-1 focus:ring-blue-400',
          className
        )}
        placeholder=""
      />
    );
  }
);

CarrySpace.displayName = 'CarrySpace';
