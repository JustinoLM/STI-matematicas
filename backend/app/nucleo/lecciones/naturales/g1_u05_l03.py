"""
g1-u05-l03 "Restemos con números hasta 19" (1.º grado, unidad 5).

Panamáticas 1.º, U5 L3 (clases 3.1 a 3.6): restar 10 a un número de 11 a 19; restar un número de
una cifra sin cruzar la decena, descomponiendo el minuendo en 10 y unidades (19 − 7: de 9 quito 7,
10 y 2 forman 12); y cruzándola, restando del 10 (13 − 9: de 10 quito 9 y queda 1, 1 y 3 forman 4).

- Forma de pasos (PROPORCION_PASOS): `19 − 7 = 10 + _ = _` y `13 − 9 = _ + 3 = _`.
- Mitad de los problemas de una cifra cruzan la decena (PROPORCION_CRUZA).
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    PASOS,
    RESTA,
    GeneradorNaturales,
    Planteo,
    pasos_resta_hasta_19,
)
from app.nucleo.lecciones.naturales.reglas import (
    R_CONFUNDIO,
    R_COPIO,
    R_DECENA,
    R_MENOR_DEL_MAYOR,
    R_PASO,
    R_SUMO,
    R_UNO_MAS,
    R_UNO_MENOS,
)
from app.nucleo.modos import ModosProblema


class RestemosHasta19(GeneradorNaturales):
    leccion_id = "g1-u05-l03"
    caminos = ("naturales.resta",)
    version = 1

    PROPORCION_MENOS_10 = 0.15
    PROPORCION_CRUZA = 0.5
    PROPORCION_PASOS = 0.5
    REGLAS = (R_CONFUNDIO, R_SUMO, R_MENOR_DEL_MAYOR, R_PASO, R_UNO_MENOS, R_UNO_MAS, R_DECENA, R_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        if rng.random() < self.PROPORCION_MENOS_10:
            return Planteo([rng.randint(11, 19), 10], [RESTA])
        if rng.random() < self.PROPORCION_CRUZA:
            a = rng.randint(11, 18)
            b = rng.randint(a % 10 + 1, 9)
        else:
            a = rng.randint(11, 19)
            b = rng.randint(1, a % 10)
        if rng.random() < self.PROPORCION_PASOS:
            paso, segs = pasos_resta_hasta_19(a, b)
            return Planteo([a, b], [RESTA], forma=PASOS, paso=paso, segmentos_paso=segs)
        return Planteo([a, b], [RESTA], forma=CALCULO)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return datos["operaciones"] == [RESTA] and 11 <= a <= 19 and 1 <= b <= 10 and b < a
