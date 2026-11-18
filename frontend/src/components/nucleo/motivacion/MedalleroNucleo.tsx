/**
 * Medallero del núcleo (fase 7b): reemplaza a las medallas de nivel por operación para quien practica
 * en el núcleo. Tres grupos: hitos del camino (bronce, plata, oro), unidades completas y lecciones.
 * Una medalla ganada no se pierde aunque la lección vuelva a "en progreso".
 */

import { Loader2, Trophy } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useMedallasNucleo } from '@/hooks/useProgresoNucleo';
import type { MedallaNucleo } from '@/types/nucleo';
import { TarjetaMedalla } from './Medalla';

const GRUPOS: { tipo: MedallaNucleo['tipo']; titulo: string }[] = [
  { tipo: 'camino', titulo: 'Hitos de mis caminos' },
  { tipo: 'unidad', titulo: 'Unidades completas' },
  { tipo: 'leccion', titulo: 'Lecciones dominadas' },
];

export function MedalleroNucleo() {
  const { data, isLoading } = useMedallasNucleo(true);
  if (isLoading || !data) {
    return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-slate-400" /></div>;
  }
  return (
    <div className="space-y-6" data-testid="medallero-nucleo">
      <div className="flex items-center gap-3">
        <Trophy className="h-9 w-9 text-yellow-500" />
        <div>
          <h1 className="text-3xl font-bold">Medallero</h1>
          <p className="text-slate-600">Tienes {data.obtenidas} de {data.total} medallas{data.grado ? ` de ${data.grado}.º` : ''}.</p>
        </div>
      </div>
      {GRUPOS.map((g) => {
        const medallas = data.medallas.filter((m) => m.tipo === g.tipo);
        if (medallas.length === 0) return null;
        const ordenadas = [...medallas].sort((a, b) => Number(b.obtenida) - Number(a.obtenida));
        return (
          <Card key={g.tipo}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{g.titulo} ({medallas.filter((m) => m.obtenida).length} de {medallas.length})</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {(g.tipo === 'camino' ? medallas : ordenadas).map((m) => (
                <TarjetaMedalla key={`${m.tipo}-${m.clave}-${m.grado_medalla}`} medalla={m} />
              ))}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
