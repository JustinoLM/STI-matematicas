/**
 * Teclado en pantalla para el modo teclado (y para fracciones y cantidades, que no traen banco).
 * Teclas grandes para dedos de niños; también acepta el teclado físico (dígitos y retroceso).
 */

import { useEffect } from 'react';
import { Delete } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TecladoNumericoProps {
  onDigito: (d: string) => void;
  onBorrar: () => void;
  deshabilitado?: boolean;
  /** Escuchar el teclado físico */
  teclasFisicas?: boolean;
}

const TECLA =
  'flex items-center justify-center rounded-2xl border-2 border-slate-300 bg-white text-4xl font-bold ' +
  'min-h-[4.5rem] min-w-[4.5rem] shadow-sm select-none active:bg-slate-100 disabled:opacity-40';

export function TecladoNumerico({ onDigito, onBorrar, deshabilitado, teclasFisicas = true }: TecladoNumericoProps) {
  useEffect(() => {
    if (!teclasFisicas || deshabilitado) return;
    const manejar = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) onDigito(e.key);
      else if (e.key === 'Backspace') onBorrar();
    };
    window.addEventListener('keydown', manejar);
    return () => window.removeEventListener('keydown', manejar);
  }, [onDigito, onBorrar, deshabilitado, teclasFisicas]);

  return (
    <div className="mx-auto grid w-full max-w-xs grid-cols-3 gap-3" role="group" aria-label="Teclado numérico" data-testid="teclado">
      {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(d => (
        <button key={d} type="button" className={TECLA} disabled={deshabilitado} onClick={() => onDigito(d)}>
          {d}
        </button>
      ))}
      <span />
      <button type="button" className={TECLA} disabled={deshabilitado} onClick={() => onDigito('0')}>0</button>
      <button type="button" className={cn(TECLA, 'text-slate-600')} disabled={deshabilitado} onClick={onBorrar}
        aria-label="Borrar">
        <Delete className="h-9 w-9" />
      </button>
    </div>
  );
}
