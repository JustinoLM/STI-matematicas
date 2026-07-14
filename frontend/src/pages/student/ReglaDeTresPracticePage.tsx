/**
 * Práctica de Regla de Tres (proporciones directa/inversa).
 *
 * Módulo independiente: sin pistas, sin animación de canvas, sin redención.
 * Flujo: iniciar -> mostrar problema -> verificar -> siguiente -> resumen final.
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Loader2, AlertCircle, Check, X, Scale, Home } from 'lucide-react';
import {
  reglaDeTresService,
  type ProblemaReglaTres,
  type ResumenSesionR3,
} from '@/services/reglaDeTresService';

export function ReglaDeTresPracticePage() {
  const navigate = useNavigate();

  const [sesionId, setSesionId] = useState<number | null>(null);
  const [nivel, setNivel] = useState(1);
  const [cantidadProblemas, setCantidadProblemas] = useState(0);
  const [progresoActual, setProgresoActual] = useState(0);
  const [problemaActual, setProblemaActual] = useState<ProblemaReglaTres | null>(null);

  const [respuesta, setRespuesta] = useState('');
  const [mostrarFeedback, setMostrarFeedback] = useState(false);
  const [esCorrecto, setEsCorrecto] = useState(false);
  const [resultadoCorrecto, setResultadoCorrecto] = useState<string | number | null>(null);
  const [siguienteProblema, setSiguienteProblema] = useState<ProblemaReglaTres | null>(null);
  const [resumenPendiente, setResumenPendiente] = useState<ResumenSesionR3 | null>(null);

  const [sesionCompletada, setSesionCompletada] = useState(false);
  const [resumen, setResumen] = useState<ResumenSesionR3 | null>(null);

  const [cargandoInicio, setCargandoInicio] = useState(true);
  const [errorInicio, setErrorInicio] = useState<string | null>(null);

  const iniciar = useCallback(() => {
    setCargandoInicio(true);
    setErrorInicio(null);
    reglaDeTresService
      .iniciarPractica()
      .then((data) => {
        setSesionId(data.sesion_id);
        setNivel(data.nivel_al_iniciar);
        setCantidadProblemas(data.cantidad_problemas);
        setProgresoActual(data.progreso_actual);
        setProblemaActual(data.problema_actual);
        setSesionCompletada(false);
        setResumen(null);
        setSiguienteProblema(null);
        setResumenPendiente(null);
        setMostrarFeedback(false);
        setRespuesta('');
      })
      .catch((err) => setErrorInicio(err instanceof Error ? err.message : 'Error al iniciar la práctica'))
      .finally(() => setCargandoInicio(false));
  }, []);

  useEffect(() => {
    iniciar();
  }, [iniciar]);

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!sesionId || !problemaActual) throw new Error('Sesión no lista');
      return reglaDeTresService.enviarRespuesta(sesionId, problemaActual.id, respuesta);
    },
    onSuccess: (data) => {
      setEsCorrecto(data.es_correcto);
      setResultadoCorrecto(data.resultado_correcto);
      setMostrarFeedback(true);
      setProgresoActual(data.progreso_actual);
      if (data.sesion_completada) {
        setResumenPendiente(data.resumen);
      } else {
        setSiguienteProblema(data.siguiente_problema);
      }
    },
  });

  const handleSiguiente = () => {
    if (resumenPendiente) {
      setSesionCompletada(true);
      setResumen(resumenPendiente);
    } else if (siguienteProblema) {
      setProblemaActual(siguienteProblema);
      setSiguienteProblema(null);
    }
    setMostrarFeedback(false);
    setRespuesta('');
  };

  if (cargandoInicio) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
        <p className="text-muted-foreground">Preparando tu práctica de Regla de Tres...</p>
      </div>
    );
  }

  if (errorInicio) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-muted-foreground">{errorInicio}</p>
        <Button onClick={iniciar}>Reintentar</Button>
      </div>
    );
  }

  if (sesionCompletada && resumen) {
    return (
      <div className="max-w-lg mx-auto mt-8">
        <Card>
          <CardHeader className="text-center">
            <Scale className="h-10 w-10 mx-auto text-primary mb-2" />
            <CardTitle>¡Práctica completada!</CardTitle>
            <CardDescription>Regla de Tres — resumen de tu sesión</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center">
              <p className="text-4xl font-bold">{resumen.nota_pct.toFixed(1)}%</p>
              <p className="text-sm text-muted-foreground">
                {resumen.correctos} de {resumen.total} correctas
              </p>
            </div>
            <div className="flex items-center justify-center gap-6 text-sm">
              <div className="text-center">
                <p className="font-semibold">{resumen.nivel_actual}</p>
                <p className="text-muted-foreground">Nivel actual</p>
              </div>
              <div className="text-center">
                <p className="font-semibold">+{resumen.puntos_ganados}</p>
                <p className="text-muted-foreground">Puntos ganados</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => navigate('/student/dashboard')}>
                <Home className="h-4 w-4 mr-2" /> Inicio
              </Button>
              <Button className="flex-1" onClick={iniciar}>
                Practicar de nuevo
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!problemaActual) return null;

  const progreso = cantidadProblemas > 0 ? Math.round((progresoActual / cantidadProblemas) * 100) : 0;

  return (
    <div className="max-w-lg mx-auto mt-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">Regla de Tres</h1>
          <Badge variant="secondary">Nivel {nivel}</Badge>
        </div>
        <span className="text-sm text-muted-foreground">
          {progresoActual} / {cantidadProblemas}
        </span>
      </div>
      <Progress value={progreso} />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            Proporción {problemaActual.tipo === 'directa' ? 'directa' : 'inversa'}
            <Badge variant={problemaActual.tipo === 'directa' ? 'default' : 'outline'}>
              {problemaActual.tipo === 'directa' ? 'a más, más' : 'a más, menos'}
            </Badge>
          </CardTitle>
          <CardDescription>Encuentra el valor de x que completa la proporción</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center text-2xl font-mono tracking-wide">
            {String(problemaActual.numero1)} : {String(problemaActual.numero2)} &nbsp;::&nbsp;{' '}
            {String(problemaActual.numero3)} : x
          </div>

          {!mostrarFeedback ? (
            <div className="flex gap-2">
              <Input
                type="number"
                inputMode="decimal"
                placeholder="Tu respuesta"
                value={respuesta}
                onChange={(e) => setRespuesta(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && respuesta.trim() !== '') submitMutation.mutate();
                }}
                autoFocus
              />
              <Button
                onClick={() => submitMutation.mutate()}
                disabled={respuesta.trim() === '' || submitMutation.isPending}
              >
                {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verificar'}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div
                className={`flex items-center gap-2 rounded-md p-3 text-sm ${
                  esCorrecto ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                }`}
              >
                {esCorrecto ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                {esCorrecto ? (
                  '¡Correcto!'
                ) : (
                  <span>
                    La respuesta correcta era <strong>{String(resultadoCorrecto)}</strong>
                  </span>
                )}
              </div>
              <Button className="w-full" onClick={handleSiguiente}>
                Siguiente
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
