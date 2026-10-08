/**
 * Modal de pistas con 3 niveles.
 */

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Lightbulb, Lock, Sparkles } from 'lucide-react';

interface HintModalProps {
  open: boolean;
  onClose: () => void;
  onRequestHint: (nivel: 1 | 2 | 3) => void;
  puntosDisponibles: number;
  pistasUsadas: number[];
  /** Niveles que el profesor deshabilitó para el grupo */
  nivelesDeshabilitados?: number[];
}

export function HintModal({
  open,
  onClose,
  onRequestHint,
  puntosDisponibles,
  pistasUsadas,
  nivelesDeshabilitados = [],
}: HintModalProps) {
  const niveles = [
    {
      nivel: 1 as const,
      titulo: 'Pista Nivel 1',
      descripcion: 'Estrategia general',
      costo: 0,
      icon: Lightbulb,
      color: 'bg-blue-100 text-blue-700',
    },
    {
      nivel: 2 as const,
      titulo: 'Pista Nivel 2',
      descripcion: 'Paso a paso',
      costo: 0,
      icon: Lightbulb,
      color: 'bg-purple-100 text-purple-700',
    },
    {
      nivel: 3 as const,
      titulo: 'Pista Nivel 3',
      descripcion: 'Casi la respuesta',
      costo: 10,
      icon: Sparkles,
      color: 'bg-yellow-100 text-yellow-700',
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500" />
            Solicitar Pista
          </DialogTitle>
          <DialogDescription>
            Selecciona el nivel de ayuda que necesitas
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {niveles.map((nivel) => {
            const Icon = nivel.icon;
            const yaUsada = pistasUsadas.includes(nivel.nivel);
            const deshabilitada = nivelesDeshabilitados.includes(nivel.nivel);
            const puedeComprar = nivel.costo === 0 || puntosDisponibles >= nivel.costo;

            return (
              <Card
                key={nivel.nivel}
                className={`${yaUsada || deshabilitada ? 'opacity-50' : ''} ${nivel.color} border-2`}
              >
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="h-8 w-8" />
                      <div>
                        <h3 className="font-bold text-lg">{nivel.titulo}</h3>
                        <p className="text-sm">{nivel.descripcion}</p>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                      {nivel.costo > 0 && (
                        <div className="flex items-center gap-1 text-sm font-bold">
                          <Sparkles className="h-4 w-4" />
                          {nivel.costo} puntos
                        </div>
                      )}
                      
                      {deshabilitada ? (
                        <Button variant="outline" disabled size="sm">
                          <Lock className="h-4 w-4 mr-2" />
                          Desactivada por tu profesor
                        </Button>
                      ) : yaUsada ? (
                        <Button variant="outline" disabled size="sm">
                          Ya usada
                        </Button>
                      ) : !puedeComprar ? (
                        <Button variant="outline" disabled size="sm">
                          <Lock className="h-4 w-4 mr-2" />
                          Sin puntos
                        </Button>
                      ) : (
                        <Button
                          onClick={() => {
                            onRequestHint(nivel.nivel);
                            onClose();
                          }}
                          size="sm"
                        >
                          {nivel.costo === 0 ? 'Ver Gratis' : 'Usar Pista'}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="text-center text-sm text-gray-600 pt-4 border-t">
          Puntos disponibles: <span className="font-bold">{puntosDisponibles}</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
