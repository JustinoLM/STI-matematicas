/**
 * Banco de respuestas para ARRASTRAR al hueco (no se toca para responder: según Khan Academy
 * Kids, tocar favorece las respuestas al azar). Funciona con ratón, con toque y con teclado
 * (sensores de @dnd-kit en ProblemaNucleo).
 *
 * Las fichas no se gastan: la que está en el hueco se ve marcada y el niño puede arrastrar otra
 * encima para cambiarla (se registra como cambio de opción).
 */

import { useDraggable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';

export const ID_FICHA = (huecoId: string, valor: string) => `ficha:${huecoId}:${valor}`;

export interface DatosFicha {
  huecoId: string;
  valor: string;
  texto: string;
}

export const CLASES_FICHA =
  'inline-flex items-center justify-center rounded-2xl border-4 border-sky-600 bg-sky-100 text-sky-950 ' +
  'font-bold text-5xl min-h-[6rem] min-w-[6rem] px-3 shadow-md select-none';

function Ficha({ huecoId, valor, texto, enHueco, deshabilitada }: DatosFicha & { enHueco: boolean; deshabilitada?: boolean }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: ID_FICHA(huecoId, valor),
    data: { huecoId, valor, texto } satisfies DatosFicha,
    disabled: deshabilitada,
  });
  return (
    <button
      ref={setNodeRef}
      type="button"
      {...listeners}
      {...attributes}
      aria-label={`Ficha ${texto}. Arrástrala al espacio.`}
      data-testid={`ficha-${valor}`}
      style={{ touchAction: 'none' }}
      className={cn(
        CLASES_FICHA,
        'cursor-grab active:cursor-grabbing',
        enHueco && 'border-dashed bg-sky-50 text-sky-700',
        isDragging && 'opacity-30',
        deshabilitada && 'cursor-not-allowed opacity-50',
      )}
    >
      {texto}
    </button>
  );
}

interface BancoRespuestasProps {
  huecoId: string;
  fichas: { valor: string; texto: string }[];
  /** Valor que ya está en el hueco */
  valorEnHueco?: string;
  deshabilitado?: boolean;
}

export function BancoRespuestas({ huecoId, fichas, valorEnHueco, deshabilitado }: BancoRespuestasProps) {
  return (
    <div
      role="group"
      aria-label="Respuestas para arrastrar"
      data-testid="banco"
      className={cn(
        'flex flex-wrap items-center justify-center gap-4 rounded-3xl bg-slate-100/80 p-4 md:landscape:gap-3 md:landscape:p-2',
        // Con 4 opciones en la columna de respuesta (horizontal): 2 × 2 en vez de 3 + 1
        fichas.length === 4 && 'md:landscape:grid md:landscape:grid-cols-2 md:landscape:justify-items-center',
      )}
    >
      {fichas.map(f => (
        <Ficha key={f.valor} huecoId={huecoId} valor={f.valor} texto={f.texto}
          enHueco={valorEnHueco === f.valor} deshabilitada={deshabilitado} />
      ))}
    </div>
  );
}
