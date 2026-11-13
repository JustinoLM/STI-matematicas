"""
g1-u06-l03 "Formemos números con unidades y decenas" (1.º grado, unidad 6).

Panamáticas 1.º, clases 3.1 a 3.4: componer y descomponer números hasta 99 (40 y 3 forman 43;
77 son 70 y 7), decenas y unidades (2 D y 5 U forman 25; 53 son 5 D y 3 U). La guía advierte
el error de descomponer por cifras (64 → 6 y 4, en vez de 60 y 4).

- Decenas y unidades (35 %): `53 = _ decenas y _ unidades`.
- Componer (25 %): `4 decenas y 3 unidades = _`.
- Decena completa y unidades (20 %): `40 y 3 forman _`.
- Descomponer (20 %): `77 = _ y _` (70 y 7).
- Números del 11 al 99; decenas completas (60 = 60 y 0) en un 10 %. Íconos de apoyo (barras y
  sueltos) según la configuración.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    COMPONER,
    DECENAS,
    DESCOMPONER,
    FORMAR,
    GeneradorNumeracion,
    componer,
    decenas_y_unidades,
    descomponer,
    formar,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    BARRAS_COMO_UNIDADES,
    CIFRAS_SEPARADAS,
    CONFUNDIO_DU,
    DECENA_COMPLETA,
    DECENA_DE_MAS,
    DECENA_DE_MENOS,
    ESCRIBIO_EL_TOTAL,
    FORMAR_COPIO,
    FORMAR_JUNTO,
    FORMAR_VALOR_POSICIONAL,
    POR_CIFRAS,
    SOLO_UNIDADES,
    UNO_MAS,
    UNO_MENOS,
)


class DecenasYUnidades(GeneradorNumeracion):
    leccion_id = "g1-u06-l03"
    version = 1
    admite_iconos = True
    FORMAS = {DECENAS: 0.35, COMPONER: 0.25, FORMAR: 0.2, DESCOMPONER: 0.2}
    PROPORCION_DECENA_COMPLETA = 0.1
    REGLAS = (CONFUNDIO_DU, DECENA_COMPLETA, POR_CIFRAS, ESCRIBIO_EL_TOTAL, BARRAS_COMO_UNIDADES, CIFRAS_SEPARADAS,
              FORMAR_VALOR_POSICIONAL, FORMAR_JUNTO, FORMAR_COPIO, SOLO_UNIDADES, UNO_MENOS, UNO_MAS,
              DECENA_DE_MENOS, DECENA_DE_MAS)

    def numero(self, rng: random.Random) -> int:
        if rng.random() < self.PROPORCION_DECENA_COMPLETA:
            return 10 * rng.randint(2, 9)
        return rng.choice([n for n in range(11, 100) if n % 10])

    def forma_decenas(self, rng):
        return decenas_y_unidades(self.numero(rng))

    def forma_componer(self, rng):
        return componer(self.numero(rng))

    def forma_formar(self, rng):
        n = rng.choice([n for n in range(21, 100) if n % 10])
        return formar(n // 10 * 10, n % 10)

    def forma_descomponer(self, rng):
        return descomponer(self.numero(rng))

    def rango_ok(self, datos, forma):
        if forma in (DECENAS, COMPONER, DESCOMPONER):
            return 11 <= datos["n"] <= 99
        if forma == FORMAR:
            d, u = datos["numeros"]
            return 20 <= d <= 90 and d % 10 == 0 and 1 <= u <= 9
        return False
