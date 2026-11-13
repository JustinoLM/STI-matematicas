"""
g1-u05-l01 "Sumemos 10" (1.º grado, unidad 5: suma y resta hasta 20).

Panamáticas 1.º, U5 L1: `10 + U` y `U + 10` (clases 1.2 y 1.3, por composición) y un número de dos
cifras más uno de una cifra sin pasar de 19 (clase 1.4: 12 + 3).

- En `12 + 3` el libro separa 12 en 10 y 2, suma 2 + 3 y junta con el 10: en la forma de pasos
  es `12 + 3 = 10 + _ = _` (PROPORCION_PASOS).
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    PASOS,
    SUMA,
    GeneradorNaturales,
    Planteo,
    lleva,
    pasos_separar_10,
)
from app.nucleo.lecciones.naturales.reglas import (
    S_CONFUNDIO,
    S_COPIO,
    S_DECENA,
    S_JUNTO_CIFRAS,
    S_PASO_SUMANDO,
    S_RESTO,
    S_UNO_MAS,
    S_UNO_MENOS,
    S_VALOR_POSICIONAL,
)
from app.nucleo.modos import ModosProblema


class Sumemos10(GeneradorNaturales):
    leccion_id = "g1-u05-l01"
    caminos = ("naturales.suma",)
    version = 1

    PROPORCION_PASOS = 0.5
    REGLAS = (S_CONFUNDIO, S_RESTO, S_PASO_SUMANDO, S_UNO_MENOS, S_UNO_MAS, S_COPIO,
              S_VALOR_POSICIONAL, S_JUNTO_CIFRAS, S_DECENA)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        tipo = rng.choice(("10+U", "U+10", "DU+U", "U+DU"))
        if tipo == "10+U":
            return Planteo([10, rng.randint(1, 9)], [SUMA])
        if tipo == "U+10":
            return Planteo([rng.randint(1, 9), 10], [SUMA])
        dos = rng.randint(11, 18)
        uno = rng.randint(1, 9 - dos % 10)
        nums = [dos, uno] if tipo == "DU+U" else [uno, dos]
        if rng.random() < self.PROPORCION_PASOS:
            paso, segs = pasos_separar_10(*nums)
            return Planteo(nums, [SUMA], forma=PASOS, paso=paso, segmentos_paso=segs)
        return Planteo(nums, [SUMA], forma=CALCULO)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return (datos["operaciones"] == [SUMA] and min(a, b) >= 1 and max(a, b) >= 10 and min(a, b) <= 9
                and a + b <= 19 and not lleva(a, b))
