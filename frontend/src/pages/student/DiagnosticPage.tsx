/**
 * Prueba diagnóstica inicial del estudiante — Sección 4.4.3
 *
 * Flujo:
 * 1. Al montar → POST /adaptive/diagnostic/start → 8 problemas (2 por operación)
 * 2. Mostrar problemas uno a uno; el estudiante escribe su respuesta y avanza
 *    (sin feedback correcto/incorrecto — es una evaluación, no una práctica)
 * 3. Al terminar → POST /adaptive/diagnostic/submit → niveles asignados
 * 4. Mostrar resultados → botón para ir a la práctica
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ClipboardList, ChevronRight, Loader2, AlertCircle, BookOpen, CheckCircle2 } from 'lucide-react';
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

interface ResultadoDiagnostico {
  perfecto: boolean;
  nivel_suma: number;
  nivel_resta: number;
  nivel_multiplicacion: number;
  nivel_division: number;
  nivel_actual: number;
  correctos_por_operacion: Record<string, number>;
  mensaje: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const OPERACION_MAP: Record<string, Operacion> = {
  '+': 'SUMA',
  '-': 'RESTA',
  '×': 'MULTIPLICACION',
  '÷': 'DIVISION',
  SUMA: 'SUMA',
  RESTA: 'RESTA',
  MULTIPLICACION: 'MULTIPLICACION',
  DIVISION: 'DIVISION',
};

const OPERACION_LABEL: Record<Operacion, string> = {
  SUMA: 'Suma',
  RESTA: 'Resta',
  MULTIPLICACION: 'Multiplicación',
  DIVISION: 'División',
};

const NIVEL_EMOJI: Record<number, string> = {
  1: '🌱',
  2: '🌿',
  3: '🌳',
  4: '🏆',
  5: '⭐',
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

interface ResultadosProps {
  resultado: ResultadoDiagnostico;
  onComenzarPractica: () => void;
}

function PantallaResultados({ resultado, onComenzarPractica }: ResultadosProps) {
  const operaciones: { key: keyof ResultadoDiagnostico; label: string; nivel: number; correctos: number }[] = [
    { key: 'nivel_suma',           label: 'Suma',           nivel: resultado.nivel_suma,           correctos: resultado.correctos_por_operacion['suma'] ?? 0 },
    { key: 'nivel_resta',          label: 'Resta',          nivel: resultado.nivel_resta,          correctos: resultado.correctos_por_operacion['resta'] ?? 0 },
    { key: 'nivel_multiplicacion', label: 'Multiplicación', nivel: resultado.nivel_multiplicacion, correctos: resultado.correctos_por_operacion['multiplicacion'] ?? 0 },
    { key: 'nivel_division',       label: 'División',       nivel: resultado.nivel_division,       correctos: resultado.correctos_por_operacion['division'] ?? 0 },
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Encabezado */}
      <Card className="text-center border-2 border-primary/30">
        <CardContent className="pt-8 pb-6">
          <div className="text-5xl mb-3">{resultado.perfecto ? '🏆' : '✅'}</div>
          <h2 className="text-2xl font-bold mb-2">¡Diagnóstico completado!</h2>
          <p className="text-muted-foreground text-sm max-w-sm mx-auto">{resultado.mensaje}</p>
          <div className="mt-4 inline-flex items-center gap-2 bg-primary/10 text-primary font-bold px-4 py-2 rounded-full text-lg">
            {NIVEL_EMOJI[resultado.nivel_actual] ?? '⭐'} Nivel inicial: {resultado.nivel_actual}
          </div>
        </CardContent>
      </Card>

      {/* Niveles por operación */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Niveles asignados por operación</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          {operaciones.map(({ label, nivel, correctos }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-lg border bg-gray-50 px-4 py-3"
            >
              <div>
                <p className="font-semibold text-sm">{label}</p>
                <p className="text-xs text-muted-foreground">{correctos}/2 correctas</p>
              </div>
              <span className="text-lg font-bold">
                {NIVEL_EMOJI[nivel] ?? '⭐'} Nivel {nivel}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* CTA */}
      <Button size="lg" className="w-full" onClick={onComenzarPractica}>
        <BookOpen className="h-5 w-5 mr-2" />
        Comenzar mi primera práctica
      </Button>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function DiagnosticPage() {
  const navigate = useNavigate();

  // ── Estado de carga ────────────────────────────────────────────────────────
  const [diagnosticoId, setDiagnosticoId] = useState<number | null>(null);
  const [problemas, setProblemas] = useState<ProblemaUI[]>([]);
  const [mensajeIntro, setMensajeIntro] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Estado de resolución ───────────────────────────────────────────────────
  const [fase, setFase] = useState<'intro' | 'resolviendo' | 'enviando' | 'resultados'>('intro');
  const [indiceActual, setIndiceActual] = useState(0);
  const [respuestaActual, setRespuestaActual] = useState('');
  const [respuestas, setRespuestas] = useState<Record<number, number>>({});
  const [limpiarKey, setLimpiarKey] = useState(0);

  // ── Resultado ─────────────────────────────────────────────────────────────
  const [resultado, setResultado] = useState<ResultadoDiagnostico | null>(null);

  // ── Teclado virtual ────────────────────────────────────────────────────────
  const lastFocusedInputRef = useRef<HTMLInputElement | null>(null);

  const problemaActual = problemas[indiceActual] ?? null;
  const progreso = problemas.length > 0
    ? Math.round(((indiceActual + 1) / problemas.length) * 100)
    : 0;

  // ── Cargar diagnóstico ────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setCargando(true);

    studentService
      .iniciarDiagnostico()
      .then((data) => {
        if (cancelled) return;
        setDiagnosticoId(data.diagnostico_id);
        setProblemas(data.problemas.map(mapearProblema));
        setMensajeIntro(data.mensaje);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        // Si ya completó el diagnóstico, redirigir a práctica
        if (err.message.includes('diagnóstico')) {
          navigate('/student/practice', { replace: true });
        } else {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setCargando(false);
      });

    return () => { cancelled = true; };
  }, [navigate]);

  // ── Rastrear el último input enfocado (para el teclado virtual) ──────────
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

  // ── Avanzar al siguiente problema ─────────────────────────────────────────
  const handleSiguiente = useCallback(async () => {
    if (!problemaActual || diagnosticoId === null) return;

    const respuestaNum = parseFloat(respuestaActual.replace(',', '.'));
    if (isNaN(respuestaNum)) return;

    // Guardar respuesta
    const nuevasRespuestas = { ...respuestas, [problemaActual.id]: respuestaNum };
    setRespuestas(nuevasRespuestas);

    if (indiceActual < problemas.length - 1) {
      // Siguiente problema
      setIndiceActual(prev => prev + 1);
      setRespuestaActual('');
      setLimpiarKey(prev => prev + 1);
    } else {
      // Último problema → enviar diagnóstico
      setFase('enviando');
      try {
        const res = await studentService.enviarDiagnostico(diagnosticoId, nuevasRespuestas);
        setResultado(res);
        setFase('resultados');
      } catch (err) {
        setError((err as Error).message);
        setFase('resolviendo');
      }
    }
  }, [problemaActual, diagnosticoId, respuestaActual, respuestas, indiceActual, problemas.length]);

  // ── Render: cargando ──────────────────────────────────────────────────────
  if (cargando) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground">Preparando tu diagnóstico...</p>
      </div>
    );
  }

  // ── Render: error ─────────────────────────────────────────────────────────
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

  // ── Render: enviando ──────────────────────────────────────────────────────
  if (fase === 'enviando') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground">Calculando tus niveles...</p>
      </div>
    );
  }

  // ── Render: resultados ────────────────────────────────────────────────────
  if (fase === 'resultados' && resultado) {
    return (
      <PantallaResultados
        resultado={resultado}
        onComenzarPractica={() => navigate('/student/practice')}
      />
    );
  }

  // ── Render: pantalla de intro ─────────────────────────────────────────────
  if (fase === 'intro') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <Card className="border-2 border-primary/30">
          <CardContent className="pt-8 pb-6 text-center space-y-4">
            <div className="text-5xl">📋</div>
            <h2 className="text-2xl font-bold">Prueba Diagnóstica</h2>
            <p className="text-muted-foreground max-w-sm mx-auto">
              {mensajeIntro || 'Antes de comenzar, realizaremos una prueba corta para conocer tu nivel y personalizar tu aprendizaje.'}
            </p>
            <div className="grid grid-cols-2 gap-3 text-left mt-4">
              <div className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
                <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">8 problemas en total (2 por cada operación)</p>
              </div>
              <div className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
                <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">Sin tiempo límite, tómatelo con calma</p>
              </div>
              <div className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
                <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">No hay retroalimentación inmediata</p>
              </div>
              <div className="flex items-start gap-2 bg-gray-50 rounded-lg p-3">
                <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">Al finalizar verás tu nivel inicial asignado</p>
              </div>
            </div>
            <Button size="lg" className="mt-2 px-8" onClick={() => setFase('resolviendo')}>
              <ClipboardList className="h-5 w-5 mr-2" />
              Comenzar diagnóstico
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Render: resolviendo ───────────────────────────────────────────────────
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
              <ClipboardList className="h-5 w-5 text-muted-foreground" />
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

      {/* Teclado + Problema en fila — teclado izquierda, problema derecha */}
      <div className="flex flex-col sm:flex-row gap-4 items-start">
        {/* Teclado virtual */}
        <div className="w-full sm:w-44 flex-shrink-0 order-last sm:order-first">
          <VirtualKeyboard
            onKeyPress={handleVirtualKeyPress}
            onDelete={handleVirtualDelete}
            onClear={handleLimpiar}
          />
        </div>

        {/* Problema */}
        <Card className="flex-1 min-w-0">
          <CardHeader>
            <CardTitle>{OPERACION_LABEL[problemaActual.operacion]}</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ProblemGrid
              key={`diag-${indiceActual}-${limpiarKey}`}
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
              <CheckCircle2 className="h-5 w-5 mr-2" />
              Finalizar diagnóstico
            </>
          ) : (
            <>
              <ChevronRight className="h-5 w-5 mr-2" />
              Siguiente problema
            </>
          )}
        </Button>
      </div>

      {/* Nota informativa */}
      <p className="text-center text-xs text-muted-foreground">
        Esta es una prueba de diagnóstico. Los resultados solo se evalúan al final.
      </p>
    </div>
  );
}
