/**
 * Modal de animación paso a paso — se muestra automáticamente cuando el estudiante
 * agota los 3 intentos de un problema.
 *
 * Muestra cómo resolver el problema con:
 *  - Un grid visual animado donde el resultado se va revelando celda por celda
 *  - El paso activo explicado en texto debajo del grid
 *  - Botón para guardar la animación en la colección personal
 */

import { useState, useEffect, useCallback } from 'react';
import { BookmarkCheck, BookmarkPlus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Operacion } from '@/types';
import { generarPasos } from '@/utils/generarPasos';
import { AnimacionGrid } from './AnimacionGrid';

// ─── Tipos ────────────────────────────────────────────────────────────────────

interface CanvasAnimationModalProps {
  open: boolean;
  onClose: () => void;
  problemaId: number;
  operacion: Operacion;
  numero1: number;
  numero2: number;
  nivelDificultad: number;
  /** Callback que guarda la animación en el backend */
  onGuardar: () => Promise<void>;
  /**
   * Si es true la animación ya fue guardada en esta sesión, el botón
   * aparece como "Guardada" desde el principio y no se puede volver a guardar.
   */
  yaGuardado?: boolean;
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const OPERACION_LABEL: Record<Operacion, string> = {
  SUMA: 'Suma',
  RESTA: 'Resta',
  MULTIPLICACION: 'Multiplicación',
  DIVISION: 'División',
};

const OPERACION_COLOR: Record<Operacion, string> = {
  SUMA: 'bg-blue-100 text-blue-800',
  RESTA: 'bg-orange-100 text-orange-800',
  MULTIPLICACION: 'bg-purple-100 text-purple-800',
  DIVISION: 'bg-green-100 text-green-800',
};

const SIMBOLO: Record<Operacion, string> = {
  SUMA: '+',
  RESTA: '−',
  MULTIPLICACION: '×',
  DIVISION: '÷',
};

const AUTO_ADVANCE_MS = 4000;

// ─── Componente ───────────────────────────────────────────────────────────────

export function CanvasAnimationModal({
  open,
  onClose,
  problemaId,
  operacion,
  numero1,
  numero2,
  nivelDificultad,
  onGuardar,
  yaGuardado = false,
}: CanvasAnimationModalProps) {
  const [pasoActual, setPasoActual] = useState(0);
  const [autoAvanzar, setAutoAvanzar] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  const pasos = generarPasos(operacion, numero1, numero2);

  // Resetear estado al abrir — preservar el estado "guardado" si ya se guardó en esta sesión
  useEffect(() => {
    if (open) {
      setPasoActual(0);
      setAutoAvanzar(true);
      setGuardado(yaGuardado); // no resetear a false si ya fue guardado
    }
  }, [open, problemaId, yaGuardado]);

  // Auto-avance entre pasos
  useEffect(() => {
    if (!open || !autoAvanzar || pasoActual >= pasos.length - 1) return;
    const timer = setTimeout(() => setPasoActual((p) => p + 1), AUTO_ADVANCE_MS);
    return () => clearTimeout(timer);
  }, [open, autoAvanzar, pasoActual, pasos.length]);

  const handleSiguiente = useCallback(() => {
    setAutoAvanzar(false);
    setPasoActual((p) => Math.min(p + 1, pasos.length - 1));
  }, [pasos.length]);

  const handleAnterior = useCallback(() => {
    setAutoAvanzar(false);
    setPasoActual((p) => Math.max(p - 1, 0));
  }, []);

  const handleGuardar = useCallback(async () => {
    if (guardado || guardando) return;
    setGuardando(true);
    try {
      await onGuardar();
      setGuardado(true);
    } finally {
      setGuardando(false);
    }
  }, [guardado, guardando, onGuardar]);

  const esFinal = pasoActual === pasos.length - 1;
  const paso = pasos[pasoActual];

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        className="max-w-2xl mx-auto"
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <span className="text-2xl">📖</span>
            ¿Cómo se resuelve?
          </DialogTitle>
        </DialogHeader>

        {/* Encabezado del problema */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <span
              className={`text-sm font-medium px-3 py-1 rounded ${OPERACION_COLOR[operacion]}`}
            >
              {OPERACION_LABEL[operacion]}
            </span>
            <Badge variant="outline" className="text-sm">
              Nivel {nivelDificultad}
            </Badge>
          </div>
          <span className="font-mono text-2xl font-bold text-gray-700">
            {numero1} {SIMBOLO[operacion]} {numero2}
          </span>
        </div>

        {/* GRID ANIMADO — elemento principal */}
        <AnimacionGrid
          operacion={operacion}
          numero1={numero1}
          numero2={numero2}
          pasoActual={pasoActual}
          totalPasos={pasos.length}
        />

        {/* Paso activo */}
        <div className="bg-gray-50 rounded-xl p-5 min-h-[100px] border border-gray-200">
          <div className="flex items-start gap-4">
            <span className="flex-shrink-0 w-9 h-9 rounded-full bg-blue-500 text-white text-base font-bold flex items-center justify-center mt-0.5">
              {pasoActual + 1}
            </span>
            <div>
              <p className="text-base font-semibold text-gray-800">{paso.titulo}</p>
              <p className="text-sm text-gray-600 mt-1.5 leading-relaxed">{paso.descripcion}</p>
            </div>
          </div>
        </div>

        {/* Indicadores de pasos */}
        <div className="flex items-center justify-center gap-2">
          {pasos.map((_, i) => (
            <button
              key={i}
              onClick={() => { setAutoAvanzar(false); setPasoActual(i); }}
              className={[
                'rounded-full transition-all duration-300',
                i === pasoActual
                  ? 'w-6 h-2.5 bg-blue-500'
                  : i < pasoActual
                  ? 'w-2.5 h-2.5 bg-blue-300'
                  : 'w-2.5 h-2.5 bg-gray-200',
              ].join(' ')}
            />
          ))}
        </div>

        {/* Auto-avance indicator */}
        {autoAvanzar && !esFinal && (
          <p className="text-center text-sm text-blue-400 -mt-1 animate-pulse">
            Avanzando automáticamente…
          </p>
        )}

        {/* Botones de control */}
        <div className="flex items-center gap-3">
          {/* Anterior */}
          <Button
            variant="outline"
            onClick={handleAnterior}
            disabled={pasoActual === 0}
            className="flex-shrink-0 px-4"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>

          {/* Siguiente */}
          <Button
            variant="outline"
            onClick={handleSiguiente}
            disabled={esFinal}
            className="flex-shrink-0 px-4"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>

          {/* Guardar */}
          <Button
            variant="outline"
            onClick={handleGuardar}
            disabled={guardando || guardado}
            className={[
              'flex-1',
              guardado ? 'border-green-400 text-green-700 bg-green-50' : '',
            ].join(' ')}
          >
            {guardado ? (
              <>
                <BookmarkCheck className="w-5 h-5 mr-2" />
                Guardada
              </>
            ) : guardando ? (
              <>
                <span className="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin inline-block" />
                Guardando…
              </>
            ) : (
              <>
                <BookmarkPlus className="w-5 h-5 mr-2" />
                Guardar animación
              </>
            )}
          </Button>

          {/* Continuar — botón principal */}
          <Button
            onClick={onClose}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-base"
          >
            Continuar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
