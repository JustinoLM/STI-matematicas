/**
 * Teclado numérico virtual.
 *
 * onMouseDown con preventDefault en cada botón evita que el botón robe el foco
 * del DigitInput activo, permitiendo que el input siga recibiendo los cambios.
 */

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Delete } from 'lucide-react';

interface VirtualKeyboardProps {
  onKeyPress: (key: string) => void;
  onDelete: () => void;
  onClear: () => void;
}

/** Previene que el click en el teclado virtual robe el foco del input activo. */
const noFocusSteal = (e: React.MouseEvent) => e.preventDefault();

export function VirtualKeyboard({ onKeyPress, onDelete, onClear }: VirtualKeyboardProps) {
  const keys = [
    ['7', '8', '9'],
    ['4', '5', '6'],
    ['1', '2', '3'],
    ['0', '.', 'C'],
  ];

  return (
    <Card className="p-2.5 bg-indigo-50 border-indigo-200">
      <div className="grid grid-cols-3 gap-1.5">
        {keys.flat().map((key) => {
          if (key === 'C') {
            return (
              <Button
                key={key}
                variant="destructive"
                size="sm"
                onClick={onClear}
                onMouseDown={noFocusSteal}
                className="h-10 text-base"
              >
                C
              </Button>
            );
          }

          return (
            <Button
              key={key}
              variant="outline"
              size="sm"
              onClick={() => onKeyPress(key)}
              onMouseDown={noFocusSteal}
              className="h-10 text-base font-bold bg-white hover:bg-blue-100 border-indigo-200"
            >
              {key}
            </Button>
          );
        })}

        {/* Botón de borrar */}
        <Button
          variant="secondary"
          size="sm"
          onClick={onDelete}
          onMouseDown={noFocusSteal}
          className="col-span-3 h-9 text-sm"
        >
          <Delete className="h-4 w-4 mr-1.5" />
          Borrar
        </Button>
      </div>
    </Card>
  );
}
