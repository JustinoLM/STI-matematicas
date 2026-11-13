"""
g1-u07-l02 "Restemos números hasta 99" (1.º grado, unidad 7), sin pedir prestado.

Panamáticas 1.º, U7 L2 (clases 2.1 a 2.7): restar decenas (50 − 40), números con unidades iguales
(57 − 17), con decenas iguales (28 − 21), decenas a un número de dos cifras (34 − 20), unidades a
un número de dos cifras (36 − 4) y dos cifras en general (38 − 15). Expresión horizontal (el libro
usa la forma vertical).

- Hueco en medio `24 − _ = 10` en una parte de los problemas (PROPORCION_FALTANTE).
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    FALTANTE,
    RESTA,
    GeneradorNaturales,
    Planteo,
    pide_prestado,
)
from app.nucleo.lecciones.naturales.reglas import (
    R_CONFUNDIO,
    R_COPIO,
    R_DECENA,
    R_FALTANTE,
    R_SUMO,
    R_UNO_MAS,
    R_UNO_MENOS,
    R_VALOR_POSICIONAL,
)
from app.nucleo.modos import ModosProblema

TIPOS = ("D0-D0", "unidades_iguales", "decenas_iguales", "DU-D0", "DU-U", "DU-DU")


class RestemosHasta99(GeneradorNaturales):
    leccion_id = "g1-u07-l02"
    caminos = ("naturales.resta",)
    version = 1

    PROPORCION_FALTANTE = 0.1
    REGLAS = (R_CONFUNDIO, R_SUMO, R_FALTANTE, R_VALOR_POSICIONAL, R_UNO_MENOS, R_UNO_MAS, R_DECENA,
              R_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        while True:
            tipo = rng.choice(TIPOS)
            d_a, u_a = rng.randint(1, 9), rng.randint(1, 9)
            a = d_a * 10 + u_a
            if tipo == "D0-D0":
                a = d_a * 10
                b = rng.randint(1, 9) * 10
            elif tipo == "unidades_iguales":
                b = rng.randint(1, 9) * 10 + u_a
            elif tipo == "decenas_iguales":
                b = d_a * 10 + rng.randint(1, 9)
            elif tipo == "DU-D0":
                b = rng.randint(1, 9) * 10
            elif tipo == "DU-U":
                b = rng.randint(1, 9)
            else:
                b = rng.randint(1, 9) * 10 + rng.randint(1, 9)
            if 1 <= b < a and not pide_prestado(a, b) and a >= 10:
                break
        forma = FALTANTE if rng.random() < self.PROPORCION_FALTANTE else CALCULO
        return Planteo([a, b], [RESTA], forma=forma, extra={"tipo": tipo})

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return (datos["operaciones"] == [RESTA] and 10 <= a <= 99 and 1 <= b < a
                and not pide_prestado(a, b))
