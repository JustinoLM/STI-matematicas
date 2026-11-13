/**
 * Un problema del núcleo: enunciado con voz, íconos, expresión con huecos (o tarjetas para
 * ordenar), banco para arrastrar o teclado, y el botón de comprobar.
 *
 * Durante el problema no hay efectos, sonidos ni animaciones: un intento incorrecto solo marca
 * en naranja el hueco y dice cuántos intentos quedan. La celebración y la solución van en la
 * pantalla entre problemas (la muestra la página al recibir onTerminado).
 *
 * El componente se monta de nuevo en cada problema (key = problema_sesion_id).
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { Check } from 'lucide-react';
import { getErrorMessage } from '@/services/api';
import { nucleoService } from '@/services/nucleoService';
import type { Problema, ProblemaTurno, Respuestas, ResultadoRespuesta, EnvioRespuesta } from '@/types/nucleo';
import { useVoz } from '@/hooks/useVoz';
import { RegistroEventos } from '@/utils/nucleo/eventos';
import { instruccion, textoParaLeer } from '@/utils/nucleo/lectura';
import { textoEnunciado, vocabularioDelTema } from '@/utils/nucleo/plantillas';
import {
  armarRespuestas,
  borrarDigito,
  camposDeHueco,
  claveCampo,
  colocarFicha,
  escribirDigito,
  fichasDeHueco,
  problemaCompleto,
  seArrastra,
  type Campo,
} from '@/utils/nucleo/respuestas';
import { BancoRespuestas, CLASES_FICHA, type DatosFicha } from './BancoRespuestas';
import { Enunciado } from './Enunciado';
import { Expresion } from './Expresion';
import { Iconos } from './Iconos';
import { Semirrecta } from './Semirrecta';
import { tarjetasDesdeNumeros, type Tarjeta } from '@/utils/nucleo/ordenar';
import { OrdenarTarjetas } from './OrdenarTarjetas';
import { TecladoNumerico } from './TecladoNumerico';

export type EnviarRespuesta = (sesionId: number, problemaSesionId: number, envio: EnvioRespuesta) => Promise<ResultadoRespuesta>;

interface ProblemaNucleoProps {
  sesionId: number;
  turno: ProblemaTurno & { problema: Problema; problema_sesion_id: number };
  icono: string;
  /** Tema narrativo del estudiante: personajes y objeto del enunciado */
  tema?: string | null;
  onTerminado: (resultado: ResultadoRespuesta, problema: Problema) => void;
  /** Inyectables para las pruebas */
  enviar?: EnviarRespuesta;
  reloj?: () => number;
}

export function ProblemaNucleo({ sesionId, turno, icono, tema, onTerminado, enviar = nucleoService.responder, reloj }: ProblemaNucleoProps) {
  const problema = turno.problema;
  const registro = useRef<RegistroEventos>();
  if (!registro.current) registro.current = new RegistroEventos(reloj);
  const voz = useVoz();

  const huecos = useMemo(() => (problema.forma === 'expresion' ? problema.huecos : []), [problema]);
  const huecosArrastre = useMemo(() => huecos.filter(seArrastra), [huecos]);
  const campos = useMemo(() => huecos.filter(h => !seArrastra(h)).flatMap(camposDeHueco), [huecos]);

  const [respuestas, setRespuestas] = useState<Respuestas>({});
  const [tarjetas, setTarjetas] = useState<Tarjeta[]>(
    problema.forma === 'ordenar' ? tarjetasDesdeNumeros(problema.numeros) : [],
  );
  const [campoActivo, setCampoActivo] = useState<Campo | null>(campos[0] ?? null);
  const [huecoBanco, setHuecoBanco] = useState<string | null>(huecosArrastre[0]?.id ?? null);
  const [arrastrando, setArrastrando] = useState<DatosFicha | null>(null);
  const [marcas, setMarcas] = useState<Set<string>>(new Set());
  const [intentosRestantes, setIntentosRestantes] = useState(turno.intentos_restantes ?? 3);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const sensores = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );

  const quitarMarca = (huecoId: string) =>
    setMarcas(m => {
      if (!m.has(huecoId)) return m;
      const n = new Set(m);
      n.delete(huecoId);
      return n;
    });

  // ── Arrastrar ────────────────────────────────────────────────────────────
  const alEmpezar = ({ active }: DragStartEvent) => setArrastrando((active.data.current as DatosFicha) ?? null);

  const alSoltar = ({ active, over }: DragEndEvent) => {
    setArrastrando(null);
    const ficha = active.data.current as DatosFicha | undefined;
    const destino = over?.data.current as { huecoId?: string } | undefined;
    if (!ficha || !destino?.huecoId || destino.huecoId !== ficha.huecoId) return;
    const { respuestas: nuevas, eventos } = colocarFicha(respuestas, ficha.huecoId, ficha.valor);
    registro.current!.registrarVarios(eventos);
    setRespuestas(nuevas);
    quitarMarca(ficha.huecoId);
    setMensaje(null);
    const siguiente = huecosArrastre.find(h => h.id !== ficha.huecoId && nuevas[h.id] === undefined);
    if (siguiente) setHuecoBanco(siguiente.id);
  };

  // ── Teclado ──────────────────────────────────────────────────────────────
  const alDigito = useCallback((d: string) => {
    if (!campoActivo) return;
    setRespuestas(r => escribirDigito(r, campoActivo, d));
    quitarMarca(campoActivo.huecoId);
  }, [campoActivo]);

  const alBorrar = useCallback(() => {
    if (!campoActivo) return;
    setRespuestas(r => borrarDigito(r, campoActivo));
  }, [campoActivo]);

  // ── Ordenar ──────────────────────────────────────────────────────────────
  const alOrdenar = (nuevas: Tarjeta[]) => {
    setTarjetas(nuevas);
    setMarcas(new Set());
    registro.current!.registrar({ tipo: 'orden_cambiado', valor: { orden: nuevas.map(t => t.valor) } });
  };

  // ── Voz ──────────────────────────────────────────────────────────────────
  const escuchar = () => {
    registro.current!.usarVoz();
    voz.hablar(textoParaLeer(problema, tema));
  };

  // ── Comprobar ────────────────────────────────────────────────────────────
  const orden = tarjetas.map(t => t.valor);
  const completo = problemaCompleto(problema, respuestas, orden);

  const comprobar = async () => {
    if (!completo || enviando) return;
    setEnviando(true);
    setMensaje(null);
    voz.callar();
    const datos = registro.current!.cerrarIntento();
    try {
      const resultado = await enviar(sesionId, turno.problema_sesion_id, {
        respuestas: armarRespuestas(problema, respuestas, orden),
        ...datos,
      });
      if (resultado.problema_terminado) {
        onTerminado(resultado, problema);
        return;
      }
      registro.current!.empezarIntento();
      setIntentosRestantes(resultado.intentos_restantes);
      setMarcas(new Set(Object.entries(resultado.huecos).filter(([, ok]) => !ok).map(([id]) => id)));
      setMensaje(
        resultado.intentos_restantes === 1
          ? 'Casi. Cambia lo que está en naranja. Te queda 1 intento.'
          : `Casi. Cambia lo que está en naranja. Te quedan ${resultado.intentos_restantes} intentos.`,
      );
    } catch (e) {
      registro.current!.reabrir(datos);
      setMensaje(getErrorMessage(e));
    } finally {
      setEnviando(false);
    }
  };

  const huecoDelBanco = huecosArrastre.find(h => h.id === huecoBanco);
  const valorEnBanco = huecoBanco ? respuestas[huecoBanco] : undefined;

  // Vertical o pantalla angosta: una columna. Horizontal desde md (tablet acostada y computadora):
  // dos columnas, a la izquierda el problema y a la derecha el banco o el teclado y "Comprobar",
  // así todo cabe sin desplazarse y el arrastre es corto, de derecha a izquierda.
  const contenido = (
    <div
      data-testid="problema"
      className="flex flex-col items-center gap-5 md:landscape:grid md:landscape:grid-cols-2 md:landscape:items-center md:landscape:gap-8"
    >
      <div className="order-1 flex w-full flex-col items-center gap-5" data-testid="columna-problema">
        <Enunciado texto={instruccion(problema)} historia={textoEnunciado(problema, tema)}
          vozDisponible={voz.disponible} onEscuchar={escuchar} />

        {/* Contar: los íconos son el problema y se dibujan siempre; si no, son apoyo opcional */}
        {problema.forma === 'expresion' && problema.presentacion?.tipo === 'conteo' ? (
          <Iconos cantidades={problema.presentacion.cantidades} icono={icono} />
        ) : problema.modos.mostrar_iconos && problema.iconos && problema.iconos.length > 0 && (
          <Iconos cantidades={problema.iconos} icono={icono} />
        )}

        {problema.forma === 'expresion' ? (
          <Expresion
            problema={problema}
            respuestas={respuestas}
            marcas={marcas}
            campoActivo={campoActivo ? claveCampo(campoActivo) : null}
            huecoBancoActivo={huecoBanco}
            onElegirCampo={setCampoActivo}
            onElegirHuecoBanco={setHuecoBanco}
            huecoArrastrando={arrastrando?.huecoId ?? null}
          />
        ) : (
          <OrdenarTarjetas tarjetas={tarjetas} ascendente={problema.ascendente} onCambio={alOrdenar}
            marcado={marcas.size > 0} deshabilitado={enviando} />
        )}
      </div>

      {/* La semirrecta necesita ancho: en vertical va entre la expresión y el banco; en horizontal,
          debajo de las dos columnas, de lado a lado. */}
      {problema.forma === 'expresion' && problema.presentacion?.tipo === 'semirrecta' && (
        <div className="order-2 flex w-full justify-center md:landscape:order-3 md:landscape:col-span-2">
          <Semirrecta presentacion={problema.presentacion} saltarin={vocabularioDelTema(tema).saltarin} />
        </div>
      )}

      <div
        className="order-3 flex w-full flex-col items-center gap-4 md:landscape:order-2 md:landscape:rounded-3xl md:landscape:bg-slate-50 md:landscape:p-4"
        data-testid="columna-respuesta"
      >
        {huecoDelBanco && (
          <BancoRespuestas
            huecoId={huecoDelBanco.id}
            fichas={fichasDeHueco(huecoDelBanco)}
            valorEnHueco={typeof valorEnBanco === 'string' ? valorEnBanco : undefined}
            deshabilitado={enviando}
          />
        )}

        {campos.length > 0 && <TecladoNumerico onDigito={alDigito} onBorrar={alBorrar} deshabilitado={enviando} />}

        {/* Alto fijo para dos líneas: el botón de comprobar no se mueve cuando aparece el mensaje */}
        <div className="flex min-h-[3.5rem] items-center justify-center" aria-live="polite">
          {mensaje && <p className="text-center text-2xl font-semibold text-orange-700" data-testid="mensaje">{mensaje}</p>}
        </div>

        <button
          type="button"
          onClick={comprobar}
          disabled={!completo || enviando}
          data-testid="comprobar"
          className="flex min-h-[4.5rem] min-w-[16rem] items-center justify-center gap-3 rounded-3xl bg-green-600 px-10 text-3xl font-bold text-white shadow-lg disabled:bg-slate-300 disabled:text-slate-500"
        >
          <Check className="h-9 w-9" />
          Comprobar
        </button>
      </div>
      <p className="sr-only">Intentos que quedan: {intentosRestantes}</p>
    </div>
  );

  if (problema.forma === 'ordenar') return contenido;
  return (
    <DndContext sensors={sensores} onDragStart={alEmpezar} onDragEnd={alSoltar} onDragCancel={() => setArrastrando(null)}
      autoScroll={false}>
      {contenido}
      <DragOverlay dropAnimation={null}>
        {arrastrando ? <span className={CLASES_FICHA}>{arrastrando.texto}</span> : null}
      </DragOverlay>
    </DndContext>
  );
}
