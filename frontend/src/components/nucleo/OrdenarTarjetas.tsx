/**
 * Ordenar números arrastrando tarjetas (forma de respuesta aparte de la expresión con huecos).
 * Ratón, toque y teclado (espacio para tomar, flechas para mover, espacio para soltar).
 * Sin transiciones: las tarjetas cambian de lugar sin animarse.
 */

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { cn } from '@/lib/utils';
import type { Tarjeta } from '@/utils/nucleo/ordenar';
import { CLASES_FICHA } from './BancoRespuestas';


/** Con 6 tarjetas o más van algo más angostas, para que quepan en una fila en la tablet vertical */
export const MUCHAS_TARJETAS = 6;

function TarjetaOrdenable({ tarjeta, marcado, deshabilitada, angosta }: {
  tarjeta: Tarjeta; marcado: boolean; deshabilitada?: boolean; angosta?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: tarjeta.id,
    transition: null,
    disabled: deshabilitada,
  });
  return (
    <button
      ref={setNodeRef}
      type="button"
      {...attributes}
      {...listeners}
      aria-label={`Tarjeta ${tarjeta.valor}`}
      data-testid={`tarjeta-${tarjeta.valor}`}
      style={{ transform: CSS.Translate.toString(transform), touchAction: 'none' }}
      className={cn(
        CLASES_FICHA,
        'cursor-grab bg-white',
        angosta && 'min-w-[5rem] px-2',
        isDragging && 'z-10 shadow-xl',
        marcado && 'border-orange-500 bg-orange-50',
      )}
    >
      {tarjeta.valor}
    </button>
  );
}

interface OrdenarTarjetasProps {
  tarjetas: Tarjeta[];
  ascendente: boolean;
  onCambio: (tarjetas: Tarjeta[]) => void;
  marcado?: boolean;
  deshabilitado?: boolean;
}

export function OrdenarTarjetas({ tarjetas, ascendente, onCambio, marcado = false, deshabilitado }: OrdenarTarjetasProps) {
  const angostas = tarjetas.length >= MUCHAS_TARJETAS;
  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const alSoltar = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const de = tarjetas.findIndex(t => t.id === active.id);
    const a = tarjetas.findIndex(t => t.id === over.id);
    if (de < 0 || a < 0) return;
    onCambio(arrayMove(tarjetas, de, a));
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex w-full items-center justify-between px-2 text-xl font-semibold text-slate-600">
        <span>{ascendente ? 'Menor' : 'Mayor'}</span>
        <span>{ascendente ? 'Mayor' : 'Menor'}</span>
      </div>
      <DndContext sensors={sensores} collisionDetection={closestCenter} onDragEnd={alSoltar} autoScroll={false}>
        {/* rectSortingStrategy: si las tarjetas no caben en una fila, se ordenan también entre filas */}
        <SortableContext items={tarjetas.map(t => t.id)} strategy={rectSortingStrategy}>
          <div className={cn('flex flex-wrap items-center justify-center', angostas ? 'gap-2.5' : 'gap-4')}
            data-testid="tarjetas">
            {tarjetas.map(t => (
              <TarjetaOrdenable key={t.id} tarjeta={t} marcado={marcado} deshabilitada={deshabilitado} angosta={angostas} />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
