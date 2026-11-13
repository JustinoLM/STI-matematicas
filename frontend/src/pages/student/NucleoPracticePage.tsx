/**
 * Práctica del núcleo (fase 4): pantalla genérica para 1.º y 2.º, en computadora y en tablet.
 * Va en paralelo a la práctica de decimales (PracticePage.tsx).
 *
 * Flujo:
 * 1. Al entrar consulta /nucleo/estado. Si hay una sesión a medias, pregunta si continuar o
 *    empezar de nuevo (descarta la anterior). Si llega desde "Continuar" del dashboard
 *    (state.retomar), continúa directamente. Al empezar o retomar, la página marca su entrada del
 *    historial con state.retomar: así, recargar en plena práctica la retoma sin preguntar
 *    (fase 5b); el aviso queda para cuando se entra con una sesión abierta.
 * 2. Problema → (intentos) → pantalla entre problemas → siguiente problema.
 * 3. Al final, el resumen. Salir a mitad deja la sesión activa para retomarla.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { AvisoSesionAMedias } from '@/components/nucleo/AvisoSesionAMedias';
import { EntreProblemas } from '@/components/nucleo/EntreProblemas';
import { ProblemaNucleo } from '@/components/nucleo/ProblemaNucleo';
import { ResumenSesion, type ResultadoProblema } from '@/components/nucleo/ResumenSesion';
import { getErrorMessage } from '@/services/api';
import { CLAVE_ESTADO_NUCLEO, nucleoService } from '@/services/nucleoService';
import { useThemeStore } from '@/store/themeStore';
import type { Problema, ProblemaTurno, ResultadoRespuesta, SesionActivaNucleo } from '@/types/nucleo';
import { iconoDelTema } from '@/utils/nucleo/iconos';

type Fase =
  | { tipo: 'cargando' }
  | { tipo: 'aviso'; sesion: SesionActivaNucleo }
  | { tipo: 'sin-lecciones' }
  | { tipo: 'problema'; turno: ProblemaTurno & { problema: Problema; problema_sesion_id: number } }
  | { tipo: 'entre'; resultado: ResultadoRespuesta; problema: Problema }
  | { tipo: 'resumen' }
  | { tipo: 'error'; mensaje: string };

export function NucleoPracticePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const temaActivoId = useThemeStore(s => s.temaActivoId);
  const retomar = (location.state as { retomar?: boolean } | null)?.retomar === true;

  const [fase, setFase] = useState<Fase>({ tipo: 'cargando' });
  const [sesion, setSesion] = useState<{ id: number; cantidad: number; progreso: number } | null>(null);
  const [resultados, setResultados] = useState<ResultadoProblema[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const iniciado = useRef(false);

  const fallar = (e: unknown) => setFase({ tipo: 'error', mensaje: getErrorMessage(e) });

  const cargarSiguiente = useCallback(async (sesionId: number) => {
    setFase({ tipo: 'cargando' });
    try {
      const turno = await nucleoService.siguiente(sesionId);
      if (turno.sesion_completada || !turno.problema || turno.problema_sesion_id == null) {
        setFase({ tipo: 'resumen' });
        return;
      }
      setSesion(s => (s ? { ...s, progreso: turno.orden ?? s.progreso } : s));
      setFase({ tipo: 'problema', turno: turno as ProblemaTurno & { problema: Problema; problema_sesion_id: number } });
    } catch (e) {
      fallar(e);
    }
  }, []);

  const ruta = location.pathname;
  const empezar = useCallback(async () => {
    setFase({ tipo: 'cargando' });
    try {
      const s = await nucleoService.iniciar();
      setSesion({ id: s.sesion_id, cantidad: s.cantidad_problemas, progreso: s.progreso });
      setResultados([]);
      queryClient.invalidateQueries({ queryKey: CLAVE_ESTADO_NUCLEO });
      // Si se recarga la página, se retoma esta sesión sin preguntar
      navigate(ruta, { replace: true, state: { retomar: true } });
      await cargarSiguiente(s.sesion_id);
    } catch (e) {
      fallar(e);
    }
  }, [cargarSiguiente, queryClient, navigate, ruta]);

  useEffect(() => {
    if (iniciado.current) return; // StrictMode monta dos veces
    iniciado.current = true;
    (async () => {
      if (retomar) return empezar();
      try {
        const estado = await nucleoService.estado();
        if (estado.sesion_activa) setFase({ tipo: 'aviso', sesion: estado.sesion_activa });
        else if (!estado.disponible) setFase({ tipo: 'sin-lecciones' });
        else await empezar();
      } catch (e) {
        fallar(e);
      }
    })();
  }, [retomar, empezar]);

  const descartarYEmpezar = async (sesionId: number) => {
    setOcupado(true);
    try {
      await nucleoService.descartar(sesionId);
      await empezar();
    } catch (e) {
      fallar(e);
    } finally {
      setOcupado(false);
    }
  };

  const alTerminarProblema = (resultado: ResultadoRespuesta, problema: Problema) => {
    setResultados(r => [...r, { correcto: resultado.correcto, experiencia: resultado.experiencia_ganada }]);
    setFase({ tipo: 'entre', resultado, problema });
  };

  const alSiguiente = (resultado: ResultadoRespuesta) => {
    if (resultado.sesion_completada || !sesion) {
      queryClient.invalidateQueries({ queryKey: CLAVE_ESTADO_NUCLEO });
      setFase({ tipo: 'resumen' });
    } else {
      cargarSiguiente(sesion.id);
    }
  };

  const salir = () => {
    queryClient.invalidateQueries({ queryKey: CLAVE_ESTADO_NUCLEO });
    navigate('/student/dashboard');
  };

  const enPractica = fase.tipo === 'problema' || fase.tipo === 'entre';

  return (
    <div className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-4xl flex-col px-4 py-3 md:landscape:max-w-6xl">
      <div className="mb-3 flex items-center justify-between">
        <button
          type="button"
          onClick={salir}
          aria-label="Salir de la práctica"
          data-testid="salir"
          className="flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-slate-300 bg-white text-slate-600"
        >
          <X className="h-9 w-9" />
        </button>
        {enPractica && sesion && (
          <span className="rounded-full bg-white/80 px-5 py-2 text-xl font-semibold text-slate-600" data-testid="contador">
            {Math.min(sesion.progreso + 1, sesion.cantidad)} de {sesion.cantidad}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col justify-center rounded-[2rem] bg-white/90 p-5 shadow-sm md:p-6">
        {fase.tipo === 'cargando' && <p className="text-center text-2xl text-slate-500">Cargando…</p>}

        {fase.tipo === 'aviso' && (
          <AvisoSesionAMedias
            sesion={fase.sesion}
            ocupado={ocupado}
            textoDescartar="Empezar de nuevo"
            onContinuar={empezar}
            onDescartar={() => descartarYEmpezar(fase.sesion.sesion_id)}
          />
        )}

        {fase.tipo === 'sin-lecciones' && (
          <p className="text-center text-2xl text-slate-700">
            Tu profesor todavía no habilitó lecciones para practicar.
          </p>
        )}

        {fase.tipo === 'problema' && sesion && (
          <ProblemaNucleo
            key={fase.turno.problema_sesion_id}
            sesionId={sesion.id}
            turno={fase.turno}
            icono={iconoDelTema(temaActivoId)}
            tema={temaActivoId}
            onTerminado={alTerminarProblema}
          />
        )}

        {fase.tipo === 'entre' && (
          <EntreProblemas resultado={fase.resultado} problema={fase.problema} onSiguiente={() => alSiguiente(fase.resultado)} />
        )}

        {fase.tipo === 'resumen' && (
          <ResumenSesion resultados={resultados} onInicio={salir} onOtra={empezar} />
        )}

        {fase.tipo === 'error' && (
          <div className="flex flex-col items-center gap-6 text-center">
            <p className="text-2xl text-red-700">{fase.mensaje}</p>
            <button type="button" onClick={salir} className="min-h-[4.5rem] rounded-2xl bg-primary px-8 text-2xl font-bold text-primary-foreground">
              Volver al inicio
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
