"""
g1-u03-l01 "Sumemos de forma horizontal" (1.º grado, unidad 3: suma y resta hasta 10).

Panamáticas 1.º, U3 L1 (clases 1.1 a 1.5): sumandos hasta 9 y totales hasta 10, más sumar 0
(clase 1.4) y las parejas que forman 10 (clase 1.3).

- Cálculo `a + b = _`: se elige el total (2 a 10) y luego el primer sumando, así todos los totales
  salen con la misma frecuencia.
- Con 0: `a + 0` o `0 + a` en una parte de los problemas (PROPORCION_CERO). Nunca con el signo
  oculto: `5 _ 0 = 5` sería ambiguo.
- Hueco en medio `a + _ = c` (PROPORCION_FALTANTE): cuánto falta para llegar al total.
- Signo oculto: `a _ b = c`.
- Versión 2: añade el 0, el hueco en medio y el enunciado con plantilla.
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    FALTANTE,
    SUMA,
    GeneradorNaturales,
    Planteo,
)
from app.nucleo.lecciones.naturales.reglas import (
    S_CONFUNDIO,
    S_COPIO,
    S_FALTANTE,
    S_RESTO,
    S_UNO_MAS,
    S_UNO_MENOS,
)
from app.nucleo.modos import ModosProblema


class SumemosHorizontal(GeneradorNaturales):
    leccion_id = "g1-u03-l01"
    caminos = ("naturales.suma",)
    version = 2

    TOTAL_MIN = 2
    TOTAL_MAX = 10
    PROPORCION_CERO = 0.1
    PROPORCION_FALTANTE = 0.15

    REGLAS = (S_CONFUNDIO, S_RESTO, S_FALTANTE, S_UNO_MENOS, S_UNO_MAS, S_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        if modos.mostrar_signo and rng.random() < self.PROPORCION_CERO:
            n = rng.randint(1, self.TOTAL_MAX)
            return Planteo([n, 0] if rng.random() < 0.5 else [0, n], [SUMA])
        total = rng.randint(self.TOTAL_MIN, self.TOTAL_MAX)
        a = rng.randint(1, total - 1)
        forma = FALTANTE if rng.random() < self.PROPORCION_FALTANTE else CALCULO
        return Planteo([a, total - a], [SUMA], forma=forma)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return (datos["operaciones"] == [SUMA] and 0 <= a <= 10 and 0 <= b <= 10
                and 1 <= a + b <= self.TOTAL_MAX)
