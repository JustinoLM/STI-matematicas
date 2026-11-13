"""
g1-u07-l03 "Sumemos y restemos en la semirrecta numérica" (1.º grado, unidad 7).

Semirrecta hasta 99 con marcas de 1 en 1 y números de 10 en 10 (Panamáticas 1.º, clases 3.1 a
3.3). Se cuenta de 1 en 1, de 5 en 5 o de 10 en 10: el segundo número es múltiplo del salto
(34 + 6, 35 + 15, 40 + 50, 90 − 35). A diferencia de U7 L1 y L2, aquí sí se cruza la decena
(35 + 15 = 50, 82 − 35 = 47 en el libro), porque en la semirrecta no hay columnas.

- Saltos de 1: avance de 2 a 12. Saltos de 5: el inicio es múltiplo de 5 y el avance de 5 a 35.
  Saltos de 10: avance de 10 a 60.
- Tramo visible: con saltos de 10, de 0 a 100; si no, de la decena anterior a la siguiente, con
  al menos 20 números (30 con saltos de 5), como en el libro (10 a 50, 50 a 90).
"""

import random

from app.nucleo.lecciones.naturales.comun import SUMA, ventana_semirrecta
from app.nucleo.lecciones.naturales.reglas import (
    R_CONFUNDIO,
    R_COPIO,
    R_DECENA,
    R_MENOR_DEL_MAYOR,
    R_SALTOS,
    R_SEMIRRECTA_REVES,
    R_SUMO,
    R_UNO_MAS,
    R_UNO_MENOS,
    S_CONFUNDIO,
    S_COPIO,
    S_DECENA,
    S_RESTO,
    S_SALTOS,
    S_SEMIRRECTA_REVES,
    S_UNO_MAS,
    S_UNO_MENOS,
)
from app.nucleo.lecciones.naturales.semirrecta import Semirrecta


class SemirrectaHasta99(Semirrecta):
    leccion_id = "g1-u07-l03"
    version = 1
    MAXIMO = 99
    SALTOS = (1, 5, 10)
    PESOS_SALTO = (0.35, 0.35, 0.3)
    AVANCE = {1: (2, 12), 5: (1, 7), 10: (1, 6)}   # saltos de 1: avance; de 5 y 10: cantidad de saltos
    REGLAS = (S_CONFUNDIO, R_CONFUNDIO, S_SEMIRRECTA_REVES, R_SEMIRRECTA_REVES, S_SALTOS, R_SALTOS,
              S_RESTO, R_SUMO, S_UNO_MENOS, S_UNO_MAS, R_UNO_MENOS, R_UNO_MAS, S_DECENA, R_DECENA,
              R_MENOR_DEL_MAYOR, S_COPIO, R_COPIO)

    def numeros(self, rng: random.Random, op: str) -> tuple[int, int, int]:
        salto = rng.choices(self.SALTOS, weights=self.PESOS_SALTO)[0]
        lo, hi = self.AVANCE[salto]
        b = rng.randint(lo, hi) * (1 if salto == 1 else salto)
        if op == SUMA:
            inicios = range(1, self.MAXIMO - b + 1)
        else:
            inicios = range(b + 1, self.MAXIMO + 1)
        if salto == 5:
            inicios = [x for x in inicios if x % 5 == 0]
        return rng.choice(list(inicios)), b, salto

    def ventana(self, inicio, llegada, salto):
        desde, hasta = ventana_semirrecta(inicio, llegada, salto, maximo=100,
                                          ancho_minimo=30 if salto == 5 else 20)
        return desde, hasta, 10

    def rango_numeros_ok(self, a, b, salto):
        if salto not in self.SALTOS:
            return False
        lo, hi = self.AVANCE[salto]
        k = b if salto == 1 else b // salto
        return lo <= k <= hi and (salto != 5 or a % 5 == 0)
