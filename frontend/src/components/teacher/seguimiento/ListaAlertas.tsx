/**
 * Alertas del núcleo (fase 6b): dificultad (el repaso automático no basta, o va detrás del salón)
 * y excelencia (acierto sostenido en la extensión). Cada una nombra estudiante y lección y ofrece
 * la acción que corresponde: asignar el prerrequisito, habilitar la lección o ver la ficha.
 */

import { EyeOff, Sparkles, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { AlertaNucleo } from '@/types/nucleo';
import { claveAlerta, textoAlerta } from '@/lib/seguimiento';

interface Props {
  alertas: AlertaNucleo[];
  soloLectura?: boolean;
  /** Muestra el salón de cada alerta (página general de alertas) */
  mostrarSalon?: boolean;
  /** Clave de la alerta cuya acción se está guardando */
  ocupada?: string | null;
  onAsignar: (a: AlertaNucleo, leccionId: string) => void;
  onHabilitar: (a: AlertaNucleo) => void;
  onOcultar: (a: AlertaNucleo) => void;
  onAbrirFicha: (a: AlertaNucleo) => void;
}

export function ListaAlertas({ alertas, soloLectura, mostrarSalon, ocupada, onAsignar, onHabilitar, onOcultar, onAbrirFicha }: Props) {
  if (alertas.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No hay alertas. Aparecen cuando alguien se atasca en una lección aunque tenga repaso, o cuando sobresale en una
        lección que todavía no está habilitada.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {alertas.map((a) => {
        const { titulo, detalle } = textoAlerta(a);
        const dificultad = a.tipo === 'dificultad';
        const clave = claveAlerta(a);
        const Icono = dificultad ? TriangleAlert : Sparkles;
        return (
          <li key={clave} data-testid={`alerta-${clave}`}
            className={`rounded-lg border p-4 ${dificultad ? 'border-red-200 bg-red-50/50' : 'border-violet-200 bg-violet-50/50'}`}>
            <div className="flex items-start gap-3">
              <Icono className={`mt-0.5 h-5 w-5 flex-shrink-0 ${dificultad ? 'text-red-600' : 'text-violet-600'}`} />
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {dificultad ? 'Dificultad' : 'Excelencia'}{mostrarSalon && ` · Salón ${a.salon_nombre}`}
                </p>
                <p className="font-semibold">{titulo}</p>
                {detalle.map((d) => <p key={d} className="text-sm text-muted-foreground">{d}</p>)}
                <div className="flex flex-wrap gap-2 pt-2">
                  {!soloLectura && a.sugerencia?.accion === 'asignar' && (
                    <Button size="sm" className="min-h-[40px]" disabled={ocupada === clave}
                      onClick={() => onAsignar(a, a.sugerencia!.leccion_id)}>
                      Asignarle «{a.sugerencia.titulo}»
                    </Button>
                  )}
                  {!soloLectura && a.sugerencia?.accion === 'habilitar' && (
                    <>
                      <Button size="sm" className="min-h-[40px]" disabled={ocupada === clave} onClick={() => onHabilitar(a)}>
                        Habilitar para el salón
                      </Button>
                      <Button size="sm" variant="outline" className="min-h-[40px]" disabled={ocupada === clave}
                        onClick={() => onAsignar(a, a.leccion_id)}>
                        Asignársela solo a {a.estudiante_nombre.split(' ')[0]}
                      </Button>
                    </>
                  )}
                  <Button size="sm" variant="outline" className="min-h-[40px]" onClick={() => onAbrirFicha(a)}>Ver ficha</Button>
                  {!soloLectura && (
                    <Button size="sm" variant="ghost" className="min-h-[40px]" disabled={ocupada === clave} onClick={() => onOcultar(a)}>
                      <EyeOff className="mr-1 h-4 w-4" /> Ocultar
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
