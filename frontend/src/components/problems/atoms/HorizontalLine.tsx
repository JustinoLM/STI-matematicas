import { cn } from '@/lib/utils';

interface HorizontalLineProps {
  width?: number | string; // pixels o string CSS
  marginLeft?: number | string; // pixels o string CSS para desplazar a la derecha
  className?: string;
}

/**
 * Línea horizontal para separar operandos de resultados
 * Usado en suma, resta, multiplicación y división
 */
export function HorizontalLine({ width, marginLeft, className }: HorizontalLineProps) {
  const widthStyle = typeof width === 'number' ? `${width}px` : width;
  const marginLeftStyle = marginLeft === undefined ? undefined : typeof marginLeft === 'number' ? `${marginLeft}px` : marginLeft;

  return (
    <div
      className={cn('border-t-2 border-gray-700', className)}
      style={{
        width: widthStyle || undefined,
        marginLeft: marginLeftStyle || undefined,
      }}
    />
  );
}
