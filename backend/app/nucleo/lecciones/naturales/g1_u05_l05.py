"""
g1-u05-l05 "Sumemos y restemos en la semirrecta numérica" (1.º grado, unidad 5).

Semirrecta de 0 a 20 con saltos de 1, todas las marcas con su número. El segundo número va de 1 a
12 (7 + 11, 16 − 11) y la llegada, de 0 a 20. Ver semirrecta.py.
"""

import random

from app.nucleo.lecciones.naturales.comun import SUMA
from app.nucleo.lecciones.naturales.reglas import (
    R_CONFUNDIO,
    R_COPIO,
    R_SEMIRRECTA_REVES,
    R_SUMO,
    R_UNO_MAS,
    R_UNO_MENOS,
    S_CONFUNDIO,
    S_COPIO,
    S_RESTO,
    S_SEMIRRECTA_REVES,
    S_UNO_MAS,
    S_UNO_MENOS,
)
from app.nucleo.lecciones.naturales.semirrecta import Semirrecta


class SemirrectaHasta20(Semirrecta):
    leccion_id = "g1-u05-l05"
    version = 1
    MAXIMO = 20
    AVANCE_MAX = 12
    REGLAS = (S_CONFUNDIO, R_CONFUNDIO, S_SEMIRRECTA_REVES, R_SEMIRRECTA_REVES, S_RESTO, R_SUMO,
              S_UNO_MENOS, S_UNO_MAS, R_UNO_MENOS, R_UNO_MAS, S_COPIO, R_COPIO)

    def numeros(self, rng: random.Random, op: str) -> tuple[int, int, int]:
        b = rng.randint(2, self.AVANCE_MAX)
        if op == SUMA:
            return rng.randint(1, self.MAXIMO - b), b, 1
        return rng.randint(b + 1, self.MAXIMO), b, 1

    def ventana(self, inicio, llegada, salto):
        return 0, self.MAXIMO, 1

    def rango_numeros_ok(self, a, b, salto):
        return salto == 1 and 1 <= b <= self.AVANCE_MAX
