"""
g1-u02-l02 "Formemos los números del 2 al 10" (1.º grado, unidad 2).

Panamáticas 1.º, clases 2.1 a 2.6: dos grupos que se unen forman un número ("2 y 1 forman 3"),
y completar la parte que falta ("2 y _ forman 4", "_ y 6 forman 6"). Fuera: escribir todas las
descomposiciones de un número.

- Formar (40 %): `3 y 4 forman _`, partes de 1 en adelante.
- Parte que falta (60 %): `2 y _ forman 7` o `_ y 6 forman 6`; una parte es 0 en un 10 %.
- Totales del 2 al 10. Íconos de apoyo en dos grupos, según la configuración.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    FORMAR,
    FORMAR_FALTANTE,
    GeneradorNumeracion,
    formar,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    FORMAR_COPIO,
    FORMAR_FALTANTE_R,
    FORMAR_RESTO,
    UNO_MAS,
    UNO_MENOS,
)


class FormarHasta10(GeneradorNumeracion):
    leccion_id = "g1-u02-l02"
    version = 1
    admite_iconos = True
    FORMAS = {FORMAR: 0.4, FORMAR_FALTANTE: 0.6}
    PROPORCION_CERO = 0.1
    REGLAS = (FORMAR_FALTANTE_R, FORMAR_COPIO, FORMAR_RESTO, UNO_MENOS, UNO_MAS)

    def forma_formar(self, rng: random.Random):
        c = rng.randint(2, 10)
        a = rng.randint(1, c - 1)
        return formar(a, c - a)

    def forma_formar_faltante(self, rng: random.Random):
        c = rng.randint(2, 10)
        a = rng.choice((0, c)) if rng.random() < self.PROPORCION_CERO else rng.randint(1, c - 1)
        return formar(a, c - a, falta=rng.randint(0, 1))

    def rango_ok(self, datos, forma):
        if forma not in self.FORMAS:
            return False
        a, b = datos["numeros"]
        return 2 <= a + b <= 10 and a >= 0 and b >= 0 and (forma == FORMAR_FALTANTE or min(a, b) >= 1)
