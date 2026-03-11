import { Trophy, Star, TrendingUp, Target, Award, ArrowRight, Brain, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Operacion } from '@/types';

interface SessionResultsProps {
  // Datos de aprendizaje
  totalProblemas: number;
  problemasCorrectos: number;
  operacionesPracticadas: Operacion[];
  nivelActual: number;
  progresoNivel: number; // Porcentaje de progreso al siguiente nivel
  operacionesDominadas: Operacion[];

  // Datos de gamificación
  puntosGanados: number;
  medallasObtenidas: string[];
  rachaActual: number;

  // Análisis LLM post-práctica (null = cargando, string = listo)
  analisisLLM?: string | null;

  // Acciones
  onContinuar: () => void;
  onVerDetalles?: () => void;
}

export function SessionResults({
  totalProblemas,
  problemasCorrectos,
  operacionesPracticadas,
  nivelActual,
  progresoNivel,
  operacionesDominadas,
  puntosGanados,
  medallasObtenidas,
  rachaActual,
  analisisLLM,
  onContinuar,
  onVerDetalles,
}: SessionResultsProps) {
  const porcentajeAciertos = Math.round((problemasCorrectos / totalProblemas) * 100);

  // Determinar mensaje motivacional según rendimiento
  const getMensajeMotivacional = () => {
    if (porcentajeAciertos === 100) {
      return {
        titulo: "¡Perfecto! 🎯",
        mensaje: "Has demostrado un dominio excepcional. ¡Sigue así!",
        color: "text-green-600"
      };
    } else if (porcentajeAciertos >= 80) {
      return {
        titulo: "¡Excelente trabajo! 🌟",
        mensaje: "Estás progresando muy bien. Sigue practicando.",
        color: "text-blue-600"
      };
    } else if (porcentajeAciertos >= 60) {
      return {
        titulo: "¡Buen esfuerzo! 💪",
        mensaje: "Vas por buen camino. La práctica te ayudará a mejorar.",
        color: "text-yellow-600"
      };
    } else {
      return {
        titulo: "¡Sigue adelante! 🚀",
        mensaje: "Cada intento te acerca más al dominio. No te rindas.",
        color: "text-orange-600"
      };
    }
  };

  const motivacion = getMensajeMotivacional();

  // Mapear operaciones a nombres legibles
  const getOperacionNombre = (op: Operacion) => {
    const nombres: Record<Operacion, string> = {
      'SUMA': 'Suma',
      'RESTA': 'Resta',
      'MULTIPLICACION': 'Multiplicación',
      'DIVISION': 'División'
    };
    return nombres[op];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Encabezado */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-800">
            ¡Sesión Completada!
          </h1>
          <p className="text-gray-600">
            Revisa tu progreso y lo que has aprendido
          </p>
        </div>

        {/* Sección 1: FEEDBACK EDUCATIVO (Principal) */}
        <Card className="border-2 border-blue-200 shadow-lg">
          <CardContent className="p-8 space-y-6">
            {/* Mensaje motivacional */}
            <div className="text-center space-y-2">
              <h2 className={`text-3xl font-bold ${motivacion.color}`}>
                {motivacion.titulo}
              </h2>
              <p className="text-lg text-gray-700">
                {motivacion.mensaje}
              </p>
            </div>

            {/* Estadísticas de aprendizaje */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Precisión */}
              <div className="bg-blue-50 p-4 rounded-lg text-center">
                <Target className="w-8 h-8 mx-auto mb-2 text-blue-600" />
                <div className="text-3xl font-bold text-blue-600">
                  {porcentajeAciertos}%
                </div>
                <div className="text-sm text-gray-600">Precisión</div>
                <div className="text-xs text-gray-500 mt-1">
                  {problemasCorrectos} de {totalProblemas} correctas
                </div>
              </div>

              {/* Nivel actual */}
              <div className="bg-purple-50 p-4 rounded-lg text-center">
                <TrendingUp className="w-8 h-8 mx-auto mb-2 text-purple-600" />
                <div className="text-3xl font-bold text-purple-600">
                  Nivel {nivelActual}
                </div>
                <div className="text-sm text-gray-600">Nivel Actual</div>
                <div className="text-xs text-gray-500 mt-1">
                  {progresoNivel}% al siguiente nivel
                </div>
              </div>

              {/* Racha */}
              <div className="bg-orange-50 p-4 rounded-lg text-center">
                <Star className="w-8 h-8 mx-auto mb-2 text-orange-600" />
                <div className="text-3xl font-bold text-orange-600">
                  {rachaActual}
                </div>
                <div className="text-sm text-gray-600">Racha de días</div>
                <div className="text-xs text-gray-500 mt-1">
                  ¡Sigue practicando!
                </div>
              </div>
            </div>

            {/* Progreso al siguiente nivel */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">
                  Progreso al Nivel {nivelActual + 1}
                </span>
                <span className="text-sm text-gray-600">
                  {progresoNivel}%
                </span>
              </div>
              <Progress value={progresoNivel} className="h-3" />
            </div>

            {/* Operaciones practicadas */}
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <Target className="w-5 h-5" />
                Operaciones Practicadas
              </h3>
              <div className="flex flex-wrap gap-2">
                {operacionesPracticadas.map((op) => (
                  <Badge
                    key={op}
                    variant="secondary"
                    className="px-3 py-1 text-sm"
                  >
                    {getOperacionNombre(op)}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Operaciones dominadas */}
            {operacionesDominadas.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                  <Award className="w-5 h-5 text-green-600" />
                  Operaciones Dominadas
                </h3>
                <div className="flex flex-wrap gap-2">
                  {operacionesDominadas.map((op) => (
                    <Badge
                      key={op}
                      className="px-3 py-1 text-sm bg-green-100 text-green-700 border-green-300"
                    >
                      ✓ {getOperacionNombre(op)}
                    </Badge>
                  ))}
                </div>
                <p className="text-sm text-gray-600 italic">
                  ¡Has alcanzado un alto nivel de precisión en estas operaciones!
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sección 2: ANÁLISIS LLM (Retroalimentación personalizada R1) */}
        <Card className="border-2 border-indigo-200 bg-indigo-50 shadow-md">
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold text-indigo-800 flex items-center gap-2 mb-3">
              <Brain className="w-5 h-5" />
              Retroalimentación personalizada
            </h2>
            {analisisLLM === null || analisisLLM === undefined ? (
              <div className="flex items-center gap-3 text-indigo-600">
                <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
                <span className="text-sm italic">Analizando tu sesión...</span>
              </div>
            ) : analisisLLM === '' ? (
              <p className="text-sm text-indigo-700 italic">
                {porcentajeAciertos >= 80
                  ? '¡Excelente sesión! Tus resultados muestran un gran dominio.'
                  : porcentajeAciertos >= 60
                  ? 'Buen trabajo. Cada práctica te ayuda a mejorar.'
                  : 'La práctica constante lleva al éxito. ¡Sigue adelante!'}
              </p>
            ) : (
              <p className="text-sm text-indigo-800 leading-relaxed">{analisisLLM}</p>
            )}
          </CardContent>
        </Card>

        {/* Sección 3: GAMIFICACIÓN (Secundaria) */}
        <Card className="border-2 border-purple-200 shadow-lg">
          <CardContent className="p-8 space-y-6">
            <h2 className="text-2xl font-bold text-gray-800 text-center flex items-center justify-center gap-2">
              <Trophy className="w-6 h-6 text-yellow-500" />
              Recompensas Obtenidas
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Puntos ganados */}
              <div className="bg-gradient-to-br from-yellow-50 to-orange-50 p-6 rounded-lg text-center border-2 border-yellow-200">
                <div className="text-5xl font-bold text-yellow-600 mb-2">
                  +{puntosGanados}
                </div>
                <div className="text-lg font-medium text-gray-700">
                  Puntos Estrella
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Usa tus puntos en la tienda
                </p>
              </div>

              {/* Medallas obtenidas */}
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 p-6 rounded-lg border-2 border-purple-200">
                <div className="text-center mb-4">
                  <Award className="w-12 h-12 mx-auto text-purple-600 mb-2" />
                  <div className="text-lg font-medium text-gray-700">
                    Medallas Desbloqueadas
                  </div>
                </div>
                {medallasObtenidas.length > 0 ? (
                  <div className="space-y-2">
                    {medallasObtenidas.map((medalla, index) => (
                      <div
                        key={index}
                        className="bg-white p-2 rounded flex items-center gap-2 text-sm"
                      >
                        <Star className="w-4 h-4 text-yellow-500" />
                        <span className="font-medium">{medalla}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 text-center">
                    Sigue practicando para desbloquear medallas
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Botones de acción */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {onVerDetalles && (
            <Button
              variant="outline"
              size="lg"
              onClick={onVerDetalles}
              className="text-lg"
            >
              Ver Detalles
            </Button>
          )}
          <Button
            size="lg"
            onClick={onContinuar}
            className="text-lg bg-blue-600 hover:bg-blue-700"
          >
            Continuar
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
}
