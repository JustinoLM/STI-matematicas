/**
 * Post-test final del estudiante.
 *
 * Mismo formato que el diagnóstico inicial (8 problemas, 2 por operación,
 * niveles 2 y 3), pero los resultados NO cambian el perfil adaptativo.
 * Al finalizar se muestra una comparación pre-test → post-test.
 *
 * Flujo:
 * 1. Montar → POST /adaptive/post-test/start → 8 problemas
 * 2. Resolver uno por uno (sin feedback inmediato)
 * 3. Finalizar → POST /adaptive/post-test/submit → resultados + comparación
 * 4. Pantalla de resultados con comparación
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ClipboardCheck, ChevronRight, Loader2, AlertCircle,
  TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import { ProblemGrid } from '@/components/problems';
import { VirtualKeyboard } from '@/components/problems/VirtualKeyboard';
import type { Operacion } from '@/types';
import { studentService, type ProblemaBE } from '@/services/studentService';

// ─── Tipos locales ────────────────────────────────────────────────────────────

interface ProblemaUI {
  id: number;
  operacion: Operacion;
  numero1: number;
  numero2: number;
  nivel_dificultad: number;
  cantidad_decimales: number;
}

interface PostTestResultado {
  perfecto: boolean;
  total_correctos: number;
  correctos_por_operacion: Record<string, number>;
  tiempos_por_operacion: Record<string, number>;
  pre_correctos_por_operacion: Record<string, number> | null;
  pre_nivel_actual: number | null;
  mensaje: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const OPERACION_MAP: Record<string, Operacion> = {
  '+': 'SUMA', '-': 'RESTA', '×': 'MULTIPLICACION', '÷': 'DIVISION',
  SUMA: 'SUMA', RESTA: 'RESTA', MULTIPLICACION: 'MULTIPLICACION', DIVISION: 'DIVISION',
};

const OPERACION_LABEL: Record<Operacion, string> = {
  SUMA: 'Suma', RESTA: 'Resta', MULTIPLICACION: 'Multiplicación', DIVISION: 'División',
};

const OP_KEY_LABEL: Record<string, string> = {
  suma: 'Suma', resta: 'Resta', multiplicacion: 'Multiplicación', division: 'División',
};

const NIVEL_EMOJI: Record<number, string> = {
  1: '🌱', 2: '🌿', 3: '🌳', 4: '🏆', 5: '⭐',
};

function mapearProblema(be: ProblemaBE): ProblemaUI {
  const op = OPERACION_MAP[String(be.operacion).toUpperCase()] ?? 'SUMA';
  return {
    id: be.id,
    operacion: op,
    numero1: Number(be.numero1),
    numero2: Number(be.numero2),
    nivel_dificultad: be.nivel_dificultad,
    cantidad_decimales: be.cantidad_decimales,
  };
}

// ─── Sub-componente: Pantalla de resultados ───────────────────────────────────

function PantallaResultados({
  resultado,
  onContinuar,
}: {
  resultado: PostTestResultado;
  onContinuar: () => void;
}) {
  const operaciones = ['suma', 'resta', 'multiplicacion', 'division'];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <Card className="text-center border-2 border-primary/30">
        <CardContent className="pt-8 pb-6">
          <div className="text-5xl mb-3">{resultado.perfecto ? '🏆' : '✅'}</div>
          <h2 className="text-2xl font-bold mb-2">¡Post-test completado!</h2>
          <p className="text-muted-foreground text-sm max-w-sm mx-auto">{resultado.mensaje}</p>
          <div className="mt-4 inline-flex items-center gap-2 bg-primary/10 text-primary font-bold px-4 py-2 rounded-full text-lg">
            {resultado.total_correctos}/8 correctas
          </div>
        </CardContent>
      </Card>

      {/* Comparación pre-test → post-test */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Comparación Pre-test → Post-test</CardTitle>
          <p className="text-xs text-muted-foreground">
            Correctas por operación (máximo 2)
          </p>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          {operaciones.map((op) => {
            const post = resultado.correctos_por_operacion[op] ?? 0;
            const pre = resultado.pre_correctos_por_operacion?.[op] ?? null;
            const diff = pre !== null ? post - pre : null;
            return (
              <div
                key={op}
                className="flex items-center justify-between rounded-lg border bg-gray-50 px-4 py-3"
              >
                <div>
                  <p className="font-semibold text-sm">{OP_KEY_LABEL[op]}</p>
                  <p className="text-xs text-muted-foreground">
                    {pre !== null ? `Antes: ${pre}/2` : 'Sin referencia'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold">Ahora: {post}/2</p>
                  {diff !== null && (
                    <div className={`flex items-center gap-1 text-xs font-medium justify-end ${
                      diff > 0 ? 'text-green-600' : diff < 0 ? 'text-red-500' : 'text-gray-500'
                    }`}>
                      {diff > 0 ? (
                        <><TrendingUp className="w-3 h-3" /> +{diff}</>
                      ) : diff < 0 ? (
                        <><TrendingDown className="w-3 h-3" /> {diff}</>
                      ) : (
                        <><Minus className="w-3 h-3" /> Sin cambio</>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Botón continuar */}
      <Button size="lg" className="w-full" onClick={onContinuar}>
        Ir al inicio
      </Button>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function PostTestPage() {
  const navigate = useNavigate();

  const [postTestId, setPostTestId] = useState<number | null>(null);
  const [problemas, setProblemas] = useState<ProblemaUI[]>([]);
  const [mensajeIntro, setMensajeIntro] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [fase, setFase] = useState<'intro' | 'resolviendo' | 'enviando' | 'resultados'>('intro');
  const [indiceActual, setIndiceActual] = useState(0);
  const [respuestaActual, setRespuestaActual] = useState('');
  const [respuestas, setRespuestas] = useState<Record<number, number>>({});
  const [limpiarKey, setLimpiarKey] = useState(0);
  const [resultado, setResultado] = useState<PostTestResultado | null>(null);

  const lastFocusedInputRef = useRef<HTMLInputElement | null>(null);
  const problemStartTimeRef = useRef<number>(Date.now());
  const [tiempos, setTiempos] = useState<Record<number, number>>({});

  const problemaActual = problemas[indiceActual] ?? null;
  const progreso = problemas.length > 0
    ? Math.round(((indiceActual + 1) / problemas.length) * 100)
    : 0;

  // ── Cargar post-test ──────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setCargando(true);

    studentService.iniciarPostTest()
      .then((data) => {
        if (cancelled) return;
        setPostTestId(data.post_test_id);
        setProblemas(data.problemas.map(mapearProblema));
        setMensajeIntro(data.mensaje);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        if (err.message.includes('ya completaste')) {
          navigate('/student/dashboard', { replace: true });
        } else {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setCargando(false);
      });

    return () => { cancelled = true; };
  }, [navigate]);

  // ── Teclado virtual ──────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: FocusEvent) => {
      const el = e.target as HTMLInputElement;
      if (el.tagName === 'INPUT') lastFocusedInputRef.current = el;
    };
    document.addEventListener('focusin', handler);
    return () => document.removeEventListener('focusin', handler);
  }, []);

  const handleVirtualKeyPress = useCallback((key: string) => {
    const el = lastFocusedInputRef.current;
    if (!el) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
    if (setter) {
      setter.call(el, key);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }, []);

  const handleVirtualDelete = useCallback(() => {
    const el = lastFocusedInputRef.current;
    if (!el) return;
    if (el.value !== '') {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
      if (setter) {
        setter.call(el, '');
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
    } else {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace', bubbles: true, cancelable: true }));
    }
  }, []);

  const handleLimpiar = useCallback(() => {
    setRespuestaActual('');
    setLimpiarKey(prev => prev + 1);
  }, []);

  // ── Avanzar al siguiente problema ────────────────────────────────────────
  const handleSiguiente = useCallback(async () => {
    if (!problemaActual || postTestId === null) return;

    const respuestaNum = parseFloat(respuestaActual.replace(',', '.'));
    if (isNaN(respuestaNum)) return;

    // Registrar tiempo
    const elapsed = Math.round((Date.now() - problemStartTimeRef.current) / 1000);
    const nuevosTiempos = { ...tiempos, [problemaActual.id]: elapsed };
    setTiempos(nuevosTiempos);

    const nuevasRespuestas = { ...respuestas, [problemaActual.id]: respuestaNum };
    setRespuestas(nuevasRespuestas);

    if (indiceActual < problemas.length - 1) {
      problemStartTimeRef.current = Date.now();
      setIndiceActual(prev => prev + 1);
      setRespuestaActual('');
      setLimpiarKey(prev => prev + 1);
    } else {
      setFase('enviando');
      try {
        const res = await studentService.enviarPostTest(postTestId, nuevasRespuestas, nuevosTiempos);
        setResultado(res);
        setFase('resultados');
      } catch (err) {
        setError((err as Error).message);
        setFase('resolviendo');
      }
    }
  }, [problemaActual, postTestId, respuestaActual, respuestas, tiempos, indiceActual, problemas.length]);

  // ── Renders ───────────────────────────────────────────────────────────────

  if (cargando) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground">Preparando tu evaluación final...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto mt-20 space-y-4">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/student/dashboard')} className="w-full">
          Volver al inicio
        </Button>
      </div>
    );
  }

  if (fase === 'enviando') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground">Calculando tus resultados finales...</p>
      </div>
    );
  }

  if (fase === 'resultados' && resultado) {
    return (
      <PantallaResultados
        resultado={resultado}
        onContinuar={() => navigate('/student/dashboard')}
      />
    );
  }

  if (fase === 'intro') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <Card className="border-2 border-primary/30">
          <CardContent className="pt-8 pb-6 text-center space-y-4">
            <div className="text-5xl">📊</div>
            <h2 className="text-2xl font-bold">Evaluación Final</h2>
            <p className="text-muted-foreground max-w-sm mx-auto">
              {mensajeIntro || 'Esta es tu evaluación final. Nos ayudará a medir cuánto has mejorado desde el inicio.'}
            </p>
            <div className="grid grid-cols-2 gap-3 text-left mt-4">
              {[
                '8 problemas en total (2 por cada operación)',
                'Sin tiempo límite, tómatelo con calma',
                'No hay retroalimentación inmediata',
                'Al finalizar verás tu comparación con el inicio',
              ].map((text) => (
                <div key={text} className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
                  <ClipboardCheck className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-gray-700">{text}</p>
                </div>
              ))}
            </div>
            <Button size="lg" className="mt-2 px-8" onClick={() => {
              problemStartTimeRef.current = Date.now();
              setFase('resolviendo');
            }}>
              <ClipboardCheck className="h-5 w-5 mr-2" />
              Comenzar evaluación final
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!problemaActual) return null;

  const puedeAvanzar = respuestaActual.trim() !== '' && !isNaN(parseFloat(respuestaActual.replace(',', '.')));
  const esUltimo = indiceActual === problemas.length - 1;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header con progreso */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <ClipboardCheck className="h-5 w-5 text-muted-foreground" />
              <h2 className="text-lg font-bold">
                Problema {indiceActual + 1} de {problemas.length}
              </h2>
              <span className="text-sm text-muted-foreground">
                {OPERACION_LABEL[problemaActual.operacion]}
              </span>
            </div>
            <span className="text-sm text-muted-foreground">
              Nivel {problemaActual.nivel_dificultad}
            </span>
          </div>
          <Progress value={progreso} className="h-2" />
        </CardContent>
      </Card>

      {/* Teclado + Problema */}
      <div className="flex flex-col sm:flex-row gap-4 items-start">
        <div className="w-full sm:w-44 flex-shrink-0 order-last sm:order-first">
          <VirtualKeyboard
            onKeyPress={handleVirtualKeyPress}
            onDelete={handleVirtualDelete}
            onClear={handleLimpiar}
          />
        </div>
        <Card className="flex-1 min-w-0">
          <CardHeader>
            <CardTitle>{OPERACION_LABEL[problemaActual.operacion]}</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ProblemGrid
              key={`pt-${indiceActual}-${limpiarKey}`}
              operacion={problemaActual.operacion}
              numero1={problemaActual.numero1}
              numero2={problemaActual.numero2}
              resultado={
                problemaActual.operacion === 'DIVISION'
                  ? parseFloat((problemaActual.numero1 / problemaActual.numero2).toFixed(2))
                  : 0
              }
              onAnswerChange={setRespuestaActual}
              showFeedback={false}
              clearIncorrectTrigger={limpiarKey}
            />
          </CardContent>
        </Card>
      </div>

      {/* Botón siguiente */}
      <div className="flex justify-end">
        <Button
          size="lg"
          onClick={handleSiguiente}
          disabled={!puedeAvanzar}
          className="px-8"
        >
          {esUltimo ? (
            <>
              <ClipboardCheck className="h-5 w-5 mr-2" />
              Finalizar evaluación
            </>
          ) : (
            <>
              <ChevronRight className="h-5 w-5 mr-2" />
              Siguiente problema
            </>
          )}
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        Esta es tu evaluación final. Los resultados no modifican tu progreso de práctica.
      </p>
    </div>
  );
}
