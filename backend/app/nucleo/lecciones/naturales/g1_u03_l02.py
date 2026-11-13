"""
g1-u03-l02 "Restemos de forma horizontal" (1.º grado, unidad 3).

Panamáticas 1.º, U3 L2 (clases 2.1 a 2.6): minuendo hasta 10, con los sentidos de quitar,
comparar y completar; restar 0 y restar un número a sí mismo (clase 2.5).

- Cálculo `a − b = _` con 2 ≤ a ≤ 10 y 1 ≤ b < a; con 0 (`a − 0`, `a − a`) en una parte de los
  problemas, nunca con el signo oculto.
- Hueco en medio `a − _ = c`: cuántos se fueron.
- Situaciones del enunciado: quitar y comparar.
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    FALTANTE,
    RESTA,
    GeneradorNaturales,
    Planteo,
)
from app.nucleo.lecciones.naturales.reglas import (
    R_CONFUNDIO,
    R_COPIO,
    R_FALTANTE,
    R_SUMO,
    R_UNO_MAS,
    R_UNO_MENOS,
)
from app.nucleo.modos import ModosProblema


class RestemosHorizontal(GeneradorNaturales):
    leccion_id = "g1-u03-l02"
    caminos = ("naturales.resta",)
    version = 1

    MINUENDO_MAX = 10
    PROPORCION_CERO = 0.1
    PROPORCION_FALTANTE = 0.15

    REGLAS = (R_CONFUNDIO, R_SUMO, R_FALTANTE, R_UNO_MENOS, R_UNO_MAS, R_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        if modos.mostrar_signo and rng.random() < self.PROPORCION_CERO:
            a = rng.randint(1, self.MINUENDO_MAX)
            return Planteo([a, 0 if rng.random() < 0.5 else a], [RESTA], situacion="quitar")
        a = rng.randint(2, self.MINUENDO_MAX)
        b = rng.randint(1, a - 1)
        forma = FALTANTE if rng.random() < self.PROPORCION_FALTANTE else CALCULO
        return Planteo([a, b], [RESTA], forma=forma)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return datos["operaciones"] == [RESTA] and 0 <= b <= a <= self.MINUENDO_MAX and a >= 1
