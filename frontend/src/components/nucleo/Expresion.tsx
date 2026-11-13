/**
 * Expresión con huecos tipados: número, opción, fracción y cantidad con unidades.
 *
 * - Los huecos que se responden arrastrando (banco u opciones) son zonas donde se suelta una
 *   ficha; tocarlos solo elige qué banco se muestra, no coloca nada.
 * - Los campos de teclado se eligen tocándolos y se llenan con el teclado en pantalla.
 * - Sin animaciones: el resaltado al arrastrar encima y la marca de error son cambios de color.
 */

import { useDroppable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';
import type { Hueco, ProblemaExpresion, Respuestas, Segmento, ValorFraccion } from '@/types/nucleo';
import { claveCampo, seArrastra, type Campo } from '@/utils/nucleo/respuestas';

export const ID_ZONA = (huecoId: string) => `hueco:${huecoId}`;

interface ExpresionProps {
  problema: ProblemaExpresion;
  respuestas: Respuestas;
  /** Huecos marcados como incorrectos en el último intento */
  marcas?: Set<string>;
  /** Clave del campo de teclado activo (claveCampo) */
  campoActivo?: string | null;
  /** Hueco cuyo banco se muestra */
  huecoBancoActivo?: string | null;
  onElegirCampo?: (campo: Campo) => void;
  onElegirHuecoBanco?: (huecoId: string) => void;
  /** Solo lectura (solución entre problemas) */
  soloLectura?: boolean;
  /** Ficha que se arrastra ahora: resalta los huecos que la aceptan */
  huecoArrastrando?: string | null;
}

const BASE_CAJA =
  'inline-flex items-center justify-center rounded-2xl border-4 font-bold select-none min-h-[5.5rem] min-w-[5.5rem] px-3';

function textoOpcion(h: Hueco, valor: string | undefined): string {
  if (valor === undefined) return '';
  if (h.tipo === 'opcion') return h.opciones.find(o => o.id === valor)?.texto ?? valor;
  return valor;
}

function ZonaArrastre({
  hueco, valor, marcado, activo, resaltar, soloLectura, onElegir,
}: {
  hueco: Hueco;
  valor: string | undefined;
  marcado: boolean;
  activo: boolean;
  resaltar: boolean;
  soloLectura?: boolean;
  onElegir?: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: ID_ZONA(hueco.id), data: { huecoId: hueco.id }, disabled: soloLectura });
  const texto = textoOpcion(hueco, valor);
  return (
    <button
      ref={setNodeRef}
      type="button"
      disabled={soloLectura}
      onClick={onElegir}
      aria-label={texto ? `Espacio con ${texto}` : 'Espacio vacío: arrastra aquí la respuesta'}
      data-testid={`hueco-${hueco.id}`}
      data-marcado={marcado || undefined}
      className={cn(
        BASE_CAJA,
        'text-5xl',
        texto ? 'border-solid bg-white text-slate-900' : 'border-dashed bg-slate-50 text-slate-400',
        activo && !soloLectura && 'border-primary',
        !activo && !marcado && 'border-slate-400',
        resaltar && 'border-primary bg-primary/10',
        isOver && 'border-primary bg-primary/20',
        marcado && 'border-orange-500 bg-orange-50',
        soloLectura && 'border-green-600 bg-green-50 text-green-800',
      )}
    >
      {texto || '?'}
    </button>
  );
}

function CampoTeclado({
  campo, valor, activo, marcado, soloLectura, onElegir, ancho = 'min-w-[5.5rem]', etiqueta,
}: {
  campo: Campo;
  valor: string;
  activo: boolean;
  marcado: boolean;
  soloLectura?: boolean;
  onElegir?: (c: Campo) => void;
  ancho?: string;
  etiqueta: string;
}) {
  return (
    <button
      type="button"
      disabled={soloLectura}
      onClick={() => onElegir?.(campo)}
      aria-label={etiqueta}
      aria-pressed={activo}
      data-testid={`campo-${claveCampo(campo)}`}
      className={cn(
        BASE_CAJA,
        ancho,
        'text-5xl',
        valor ? 'bg-white text-slate-900' : 'bg-slate-50 text-slate-400 border-dashed',
        activo && !soloLectura ? 'border-primary ring-4 ring-primary/30' : 'border-slate-400',
        marcado && 'border-orange-500 bg-orange-50',
        soloLectura && 'border-green-600 bg-green-50 text-green-800',
      )}
    >
      {valor || '?'}
    </button>
  );
}

function FraccionFija({ numerador, denominador }: { numerador: number; denominador: number }) {
  return (
    <span className="inline-flex flex-col items-center text-4xl font-bold leading-none">
      <span>{numerador}</span>
      <span className="my-1 h-1 w-12 rounded bg-current" />
      <span>{denominador}</span>
    </span>
  );
}

export function Expresion({
  problema, respuestas, marcas, campoActivo, huecoBancoActivo, onElegirCampo, onElegirHuecoBanco,
  soloLectura, huecoArrastrando,
}: ExpresionProps) {
  const huecos = new Map(problema.huecos.map(h => [h.id, h]));

  const renderHueco = (h: Hueco) => {
    const marcado = !!marcas?.has(h.id);
    const v = respuestas[h.id];
    if (seArrastra(h)) {
      return (
        <ZonaArrastre
          hueco={h}
          valor={typeof v === 'string' ? v : undefined}
          marcado={marcado}
          activo={huecoBancoActivo === h.id}
          resaltar={huecoArrastrando === h.id}
          soloLectura={soloLectura}
          onElegir={() => onElegirHuecoBanco?.(h.id)}
        />
      );
    }
    if (h.tipo === 'numero') {
      const campo = { huecoId: h.id };
      return (
        <CampoTeclado campo={campo} valor={typeof v === 'string' ? v : ''} marcado={marcado}
          activo={campoActivo === claveCampo(campo)} soloLectura={soloLectura} onElegir={onElegirCampo}
          etiqueta="Espacio para escribir el número" />
      );
    }
    if (h.tipo === 'fraccion') {
      const f = (v && typeof v === 'object' ? v : {}) as Partial<ValorFraccion>;
      const num = { huecoId: h.id, parte: 'numerador' };
      const den = { huecoId: h.id, parte: 'denominador' };
      return (
        <span className="inline-flex flex-col items-center gap-1">
          <CampoTeclado campo={num} valor={f.numerador ?? ''} marcado={marcado} soloLectura={soloLectura}
            activo={campoActivo === claveCampo(num)} onElegir={onElegirCampo} etiqueta="Numerador" />
          <span className="h-1.5 w-full rounded bg-slate-700" />
          <CampoTeclado campo={den} valor={f.denominador ?? ''} marcado={marcado} soloLectura={soloLectura}
            activo={campoActivo === claveCampo(den)} onElegir={onElegirCampo} etiqueta="Denominador" />
        </span>
      );
    }
    if (h.tipo === 'cantidad') {
      const c = (v && typeof v === 'object' ? v : {}) as Record<string, string>;
      return (
        <span className="inline-flex flex-wrap items-center gap-2">
          {h.unidades.map(u => {
            const campo = { huecoId: h.id, parte: u };
            return (
              <span key={u} className="inline-flex items-center gap-2">
                <CampoTeclado campo={campo} valor={c[u] ?? ''} marcado={marcado} soloLectura={soloLectura}
                  activo={campoActivo === claveCampo(campo)} onElegir={onElegirCampo}
                  etiqueta={`Cantidad de ${u}`} />
                <span className="text-4xl font-semibold">{u}</span>
              </span>
            );
          })}
        </span>
      );
    }
    return null;
  };

  const renderSegmento = (s: Segmento, i: number) => {
    switch (s.tipo) {
      case 'texto':
        return <span key={i} className="text-4xl font-semibold">{s.texto}</span>;
      case 'numero':
        return <span key={i} className="text-6xl font-bold tabular-nums">{s.valor}</span>;
      case 'fraccion':
        return <FraccionFija key={i} numerador={s.numerador} denominador={s.denominador} />;
      case 'simbolo':
        return <span key={i} className="text-6xl font-bold text-slate-600" aria-label={s.simbolo}>{s.simbolo}</span>;
      case 'hueco': {
        const h = huecos.get(s.hueco_id);
        return h ? <span key={i}>{renderHueco(h)}</span> : null;
      }
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-4" data-testid="expresion">
      {problema.segmentos.map(renderSegmento)}
    </div>
  );
}
