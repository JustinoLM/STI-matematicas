/**
 * Instrucción del problema con lectura en voz alta opcional. Si el navegador no tiene voz en
 * español, el botón no aparece.
 */

import { Volume2 } from 'lucide-react';

interface EnunciadoProps {
  texto: string;
  vozDisponible: boolean;
  onEscuchar: () => void;
}

export function Enunciado({ texto, vozDisponible, onEscuchar }: EnunciadoProps) {
  return (
    <div className="flex items-center justify-center gap-4">
      <p className="text-center text-3xl font-semibold text-slate-800" data-testid="instruccion">{texto}</p>
      {vozDisponible && (
        <button
          type="button"
          onClick={onEscuchar}
          aria-label="Escuchar"
          data-testid="boton-voz"
          className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-4 border-primary bg-white text-primary shadow"
        >
          <Volume2 className="h-10 w-10" />
        </button>
      )}
    </div>
  );
}
