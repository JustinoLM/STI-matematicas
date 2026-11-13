/**
 * Enunciado del problema con lectura en voz alta opcional. Si el problema trae plantilla, el texto
 * con el tema va primero y la instrucción ("Arrastra el número que falta.") debajo, más pequeña.
 * Si el navegador no tiene voz en español, el botón no aparece.
 */

import { Volume2 } from 'lucide-react';

interface EnunciadoProps {
  texto: string;
  /** Texto de la plantilla con el tema, si el problema la trae */
  historia?: string | null;
  vozDisponible: boolean;
  onEscuchar: () => void;
}

export function Enunciado({ texto, historia, vozDisponible, onEscuchar }: EnunciadoProps) {
  return (
    <div className="flex items-center justify-center gap-4">
      {historia ? (
        <div className="flex flex-col gap-2 text-center">
          <p className="text-2xl font-semibold leading-snug text-slate-800" data-testid="enunciado">{historia}</p>
          <p className="text-lg text-slate-600 sm:text-xl" data-testid="instruccion">{texto}</p>
        </div>
      ) : (
        <p className="text-center text-3xl font-semibold text-slate-800" data-testid="instruccion">{texto}</p>
      )}
      {vozDisponible && (
        <button
          type="button"
          onClick={onEscuchar}
          aria-label="Escuchar"
          data-testid="boton-voz"
          className={`flex ${historia ? 'h-16 w-16' : 'h-20 w-20'} shrink-0 items-center justify-center rounded-full border-4 border-primary bg-white text-primary shadow`}
        >
          <Volume2 className="h-10 w-10" />
        </button>
      )}
    </div>
  );
}
