/**
 * "Mi camino" (fase 7b): nivel de jugador, avance de cada camino, el mapa del grado decorado según el
 * tema y, al tocar una parada, cuánto falta para dominar esa lección. Nada de esto aparece durante la
 * práctica. Solo para quien practica en el núcleo.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Play } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarraNivel, BarrasCamino, CasillasDominio } from '@/components/nucleo/motivacion/Barras';
import { MapaCamino } from '@/components/nucleo/motivacion/MapaCamino';
import { TEXTO_ESTADO } from '@/components/nucleo/motivacion/textos';
import { RUTA_PRACTICA_NUCLEO } from '@/hooks/useEstadoNucleo';
import { useProgresoNucleo } from '@/hooks/useProgresoNucleo';
import { useThemeStore } from '@/store/themeStore';
import type { ParadaMapa } from '@/types/nucleo';

function DetalleParada({ parada }: { parada: ParadaMapa }) {
  return (
    <div className="space-y-3" data-testid="detalle-parada">
      <p className="text-lg font-bold text-slate-800">L{parada.leccion_numero}. {parada.titulo}</p>
      <p className="text-sm text-slate-600">{TEXTO_ESTADO[parada.estado]}</p>
      {parada.estado === 'provisional' && (
        <p className="text-sm text-sky-800">Parece que ya la sabes. Practícala para confirmarlo.</p>
      )}
      {(parada.estado === 'en_progreso' || parada.estado === 'provisional' || parada.estado === 'repaso') && (
        <CasillasDominio casillas={parada.casillas} aciertos={parada.aciertos} meta={parada.meta} />
      )}
      {parada.estado === 'no_iniciado' && !parada.en_practica && (
        <p className="text-sm text-slate-600">Tu profesor la abrirá más adelante.</p>
      )}
    </div>
  );
}

export function CaminoPage() {
  const navigate = useNavigate();
  const temaActivoId = useThemeStore((s) => s.temaActivoId);
  const { enNucleo, data: progreso, isLoading } = useProgresoNucleo();
  const [elegida, setElegida] = useState<string | null>(null);

  if (!enNucleo) {
    return <p className="py-12 text-center text-lg text-slate-600">Tu camino aparecerá cuando tu profesor habilite lecciones.</p>;
  }
  if (isLoading || !progreso) {
    return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-slate-400" /></div>;
  }

  const paradas = progreso.unidades.flatMap((u) => u.lecciones);
  const idElegida = elegida ?? progreso.siguiente ?? paradas[0]?.leccion_id ?? null;
  const parada = paradas.find((p) => p.leccion_id === idElegida) ?? null;

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] landscape:md:grid-cols-[minmax(0,1fr)_17rem]">
      <div className="order-2 lg:order-1 landscape:md:order-1">
        <MapaCamino unidades={progreso.unidades} temaId={temaActivoId} grado={progreso.grado}
          elegida={idElegida} onElegir={(p) => setElegida(p.leccion_id)} />
      </div>
      <div className="order-1 space-y-4 lg:order-2 lg:sticky lg:top-20 lg:self-start landscape:md:order-2 landscape:md:sticky landscape:md:top-20 landscape:md:self-start">
        <Card>
          <CardContent className="pt-5">
            <BarraNivel nivel={progreso.nivel} enNivel={progreso.experiencia_en_nivel} paraSubir={progreso.experiencia_para_subir} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-lg">Mis caminos</CardTitle></CardHeader>
          <CardContent><BarrasCamino caminos={progreso.caminos} /></CardContent>
        </Card>
        {parada && (
          <Card>
            <CardContent className="pt-5"><DetalleParada parada={parada} /></CardContent>
          </Card>
        )}
        <button type="button" onClick={() => navigate(RUTA_PRACTICA_NUCLEO)}
          className="flex min-h-[4rem] w-full items-center justify-center gap-3 rounded-2xl bg-primary text-2xl font-bold text-primary-foreground">
          <Play className="h-7 w-7" /> Practicar
        </button>
      </div>
    </div>
  );
}
