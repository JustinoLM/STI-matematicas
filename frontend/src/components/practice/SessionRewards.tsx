import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Star, TrendingUp, Award, Coins, Sparkles } from 'lucide-react';

interface Medalla {
  id: string;
  nombre: string;
  descripcion: string;
  icono: string;
}

interface SessionRewardsProps {
  puntosGanados: number;
  monedasGanadas: number;
  medallasDesbloqueadas: Medalla[];
  nivelAnterior: number;
  nivelActual: number;
  progresoNivel: number; // 0-100
  onContinuar: () => void;
}

/**
 * Pantalla de recompensas de sesión
 * Muestra puntos, monedas, medallas y progreso de nivel con animaciones
 */
export function SessionRewards({
  puntosGanados,
  monedasGanadas,
  medallasDesbloqueadas,
  nivelAnterior,
  nivelActual,
  progresoNivel,
  onContinuar,
}: SessionRewardsProps) {
  const [animatedPuntos, setAnimatedPuntos] = useState(0);
  const [animatedMonedas, setAnimatedMonedas] = useState(0);
  const [animatedProgreso, setAnimatedProgreso] = useState(0);
  const [mostrarMedallas, setMostrarMedallas] = useState(false);
  const [mostrarNivel, setMostrarNivel] = useState(false);

  const huboSubidaDeNivel = nivelActual > nivelAnterior;

  useEffect(() => {
    // Animar puntos
    const puntosInterval = setInterval(() => {
      setAnimatedPuntos(prev => {
        if (prev >= puntosGanados) {
          clearInterval(puntosInterval);
          return puntosGanados;
        }
        return Math.min(prev + Math.ceil(puntosGanados / 30), puntosGanados);
      });
    }, 50);

    // Animar monedas
    const monedasInterval = setInterval(() => {
      setAnimatedMonedas(prev => {
        if (prev >= monedasGanadas) {
          clearInterval(monedasInterval);
          return monedasGanadas;
        }
        return Math.min(prev + Math.ceil(monedasGanadas / 30), monedasGanadas);
      });
    }, 50);

    // Animar progreso
    const progresoInterval = setInterval(() => {
      setAnimatedProgreso(prev => {
        if (prev >= progresoNivel) {
          clearInterval(progresoInterval);
          // Mostrar medallas después de completar animación
          setTimeout(() => setMostrarMedallas(true), 500);
          return progresoNivel;
        }
        return Math.min(prev + 2, progresoNivel);
      });
    }, 30);

    return () => {
      clearInterval(puntosInterval);
      clearInterval(monedasInterval);
      clearInterval(progresoInterval);
    };
  }, [puntosGanados, monedasGanadas, progresoNivel]);

  useEffect(() => {
    if (mostrarMedallas && huboSubidaDeNivel) {
      setTimeout(() => setMostrarNivel(true), 800);
    }
  }, [mostrarMedallas, huboSubidaDeNivel]);

  return (
    <div className="max-w-3xl mx-auto space-y-6 p-6">
      {/* Header con celebración */}
      <Card className="border-2 border-yellow-400 bg-gradient-to-br from-yellow-50 via-orange-50 to-amber-50 overflow-hidden relative">
        <div className="absolute inset-0 bg-gradient-to-br from-yellow-100/20 via-transparent to-orange-100/20" />
        <CardContent className="pt-10 pb-8 text-center relative z-10">
          <div className="text-8xl mb-4 animate-bounce">🎉</div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-yellow-600 to-orange-600 bg-clip-text text-transparent mb-2">
            ¡Excelente Trabajo!
          </h1>
          <p className="text-lg text-muted-foreground">
            Has ganado recompensas por tu esfuerzo
          </p>
        </CardContent>
      </Card>

      {/* Puntos y Monedas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-2 border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 transform transition-transform hover:scale-105">
          <CardContent className="pt-6 pb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-500 rounded-full">
                  <Star className="h-8 w-8 text-white" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Puntos Estrella</p>
                  <p className="text-4xl font-bold text-blue-600">
                    +{animatedPuntos}
                  </p>
                </div>
              </div>
              <Sparkles className="h-12 w-12 text-blue-400 opacity-30" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-2 border-yellow-300 bg-gradient-to-br from-yellow-50 to-amber-50 transform transition-transform hover:scale-105">
          <CardContent className="pt-6 pb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-500 rounded-full">
                  <Coins className="h-8 w-8 text-white" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Monedas</p>
                  <p className="text-4xl font-bold text-yellow-600">
                    +{animatedMonedas}
                  </p>
                </div>
              </div>
              <Sparkles className="h-12 w-12 text-yellow-400 opacity-30" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progreso de nivel */}
      <Card className="border-2 border-purple-300">
        <CardContent className="pt-6 pb-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TrendingUp className="h-6 w-6 text-purple-600" />
                <div>
                  <p className="font-semibold text-lg">Nivel {nivelActual}</p>
                  <p className="text-sm text-muted-foreground">
                    Progreso hacia el siguiente nivel
                  </p>
                </div>
              </div>
              <Badge variant="secondary" className="text-lg px-3 py-1">
                {animatedProgreso}%
              </Badge>
            </div>
            <Progress value={animatedProgreso} className="h-3" />
          </div>
        </CardContent>
      </Card>

      {/* Subida de nivel (si aplica) */}
      {huboSubidaDeNivel && mostrarNivel && (
        <Card className="border-4 border-green-400 bg-gradient-to-br from-green-50 to-emerald-50 animate-pulse">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="text-7xl mb-4">🎊</div>
            <h2 className="text-3xl font-bold text-green-700 mb-2">
              ¡Subiste de Nivel!
            </h2>
            <p className="text-xl text-green-600">
              Nivel {nivelAnterior} → Nivel {nivelActual}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Medallas desbloqueadas */}
      {mostrarMedallas && medallasDesbloqueadas.length > 0 && (
        <Card className="border-2 border-amber-300">
          <CardContent className="pt-6 pb-6">
            <div className="flex items-center gap-3 mb-4">
              <Award className="h-6 w-6 text-amber-600" />
              <h3 className="text-xl font-bold">Nuevas Medallas</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {medallasDesbloqueadas.map((medalla) => (
                <div
                  key={medalla.id}
                  className="flex items-center gap-4 p-4 bg-gradient-to-r from-amber-50 to-yellow-50 rounded-lg border border-amber-200"
                >
                  <div className="text-4xl">{medalla.icono}</div>
                  <div>
                    <p className="font-bold text-amber-900">{medalla.nombre}</p>
                    <p className="text-sm text-amber-700">{medalla.descripcion}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Botón continuar */}
      <div className="flex justify-center pt-4">
        <Button
          size="lg"
          onClick={onContinuar}
          className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 px-16 py-6 text-lg"
        >
          ¡Continuar!
        </Button>
      </div>
    </div>
  );
}
