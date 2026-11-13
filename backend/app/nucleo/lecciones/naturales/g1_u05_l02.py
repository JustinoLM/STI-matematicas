"""
g1-u05-l02 "Sumemos completando a 10" (1.º grado, unidad 5).

Panamáticas 1.º, U5 L2 (clases 2.1 a 2.4): sumas de dos números de una cifra con total de 11 a
18; uno de los sumandos se completa a 10 con parte del otro (9 + 3: 3 se separa en 1 y 2, 9 y 1
forman 10, 10 y 2 forman 12). El libro no lo considera "llevar".

- Forma de pasos (PROPORCION_PASOS): `9 + 4 = 10 + _ = _`; si el mayor es el segundo,
  `2 + 9 = _ + 10 = _`. Los huecos son lo que sobra después de completar el 10 y el total.
- En el resto, el cálculo `a + b = _` o el signo oculto.
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    PASOS,
    SUMA,
    GeneradorNaturales,
    Planteo,
    pasos_completar_10,
)
from app.nucleo.lecciones.naturales.reglas import (
    S_CONFUNDIO,
    S_COPIO,
    S_DECENA,
    S_PASO_COMPLEMENTO,
    S_PASO_SUMANDO,
    S_RESTO,
    S_UNO_MAS,
    S_UNO_MENOS,
)
from app.nucleo.modos import ModosProblema


class SumemosCompletando10(GeneradorNaturales):
    leccion_id = "g1-u05-l02"
    caminos = ("naturales.suma",)
    version = 1

    PROPORCION_PASOS = 0.5
    REGLAS = (S_CONFUNDIO, S_RESTO, S_PASO_SUMANDO, S_PASO_COMPLEMENTO, S_UNO_MENOS, S_UNO_MAS,
              S_DECENA, S_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        total = rng.randint(11, 18)
        a = rng.randint(total - 9, 9)
        nums = [a, total - a]
        if rng.random() < self.PROPORCION_PASOS:
            paso, segs = pasos_completar_10(*nums)
            return Planteo(nums, [SUMA], forma=PASOS, paso=paso, segmentos_paso=segs)
        return Planteo(nums, [SUMA], forma=CALCULO)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return datos["operaciones"] == [SUMA] and 2 <= a <= 9 and 2 <= b <= 9 and 11 <= a + b <= 18
