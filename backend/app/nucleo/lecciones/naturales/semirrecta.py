"""
Base de "Sumemos y restemos en la semirrecta numérica" (U5 L5 hasta 20 y U7 L3 hasta 99).

Panamáticas 1.º, clases 5.1 a 5.3 (U5) y 3.1 a 3.3 (U7): la suma avanza hacia la derecha y la
resta retrocede hacia la izquierda desde el primer número. Dos ejercicios:

- "semirrecta" (resolver): `a + b = _` con el punto de partida y los saltos dibujados; la llegada
  no se marca. Con el signo oculto, `a _ b = c` y la dirección de los saltos da el signo.
- "anotar" (anotar la operación que muestran los saltos): `_ _ _ = _`, con la llegada marcada.
  Solo con el signo visible en la configuración (PROPORCION_ANOTAR).

La presentación especial va en problema.presentacion (comun.semirrecta) y no lleva íconos.
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    ANOTAR,
    RESTA,
    SEMIRRECTA,
    SUMA,
    GeneradorNaturales,
    Planteo,
    operar,
    semirrecta,
)
from app.nucleo.modos import ModosProblema


class Semirrecta(GeneradorNaturales):
    caminos = ("naturales.suma", "naturales.resta")
    admite_iconos = False
    PROPORCION_ANOTAR = 0.4
    MAXIMO = 20

    def numeros(self, rng: random.Random, op: str) -> tuple[int, int, int]:   # pragma: no cover
        """(inicio, avance, salto) dentro del rango de la lección."""
        raise NotImplementedError

    def ventana(self, inicio: int, llegada: int, salto: int) -> tuple[int, int, int]:   # pragma: no cover
        """(desde, hasta, etiquetas_cada)."""
        raise NotImplementedError

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        op = rng.choice((SUMA, RESTA))
        a, b, salto = self.numeros(rng, op)
        forma = ANOTAR if modos.mostrar_signo and rng.random() < self.PROPORCION_ANOTAR else SEMIRRECTA
        llegada = operar(a, op, b)
        desde, hasta, etiquetas = self.ventana(a, llegada, salto)
        pres = semirrecta(a, op, b, salto, desde=desde, hasta=hasta, etiquetas_cada=etiquetas,
                          mostrar_llegada=forma == ANOTAR)
        return Planteo([a, b], [op], forma=forma, presentacion=pres)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        op = datos["operaciones"][0]
        salto = datos.get("salto", 1)
        r = operar(a, op, b)
        return (datos["forma"] in (SEMIRRECTA, ANOTAR) and 0 <= a <= self.MAXIMO and 0 <= r <= self.MAXIMO
                and b >= 1 and b % salto == 0 and self.rango_numeros_ok(a, b, salto))

    def rango_numeros_ok(self, a: int, b: int, salto: int) -> bool:   # pragma: no cover
        raise NotImplementedError
