"""
g1-u07-l01 "Sumemos con totales hasta 99" (1.º grado, unidad 7), sin llevar.

Panamáticas 1.º, U7 L1 (clases 1.2 a 1.6): decenas más decenas (20 + 30), unidades a un número de
dos cifras (32 + 5), dos cifras más dos cifras (25 + 34) y dos cifras más decenas (50 + 23).
El libro usa la forma vertical desde la clase 1.4; aquí la expresión es horizontal (la forma
vertical queda pendiente como presentación).

- Hueco en medio `24 + _ = 36` en una parte de los problemas (PROPORCION_FALTANTE).
"""

import random

from app.nucleo.lecciones.naturales.comun import (
    CALCULO,
    FALTANTE,
    SUMA,
    GeneradorNaturales,
    Planteo,
    lleva,
)
from app.nucleo.lecciones.naturales.reglas import (
    S_CONFUNDIO,
    S_COPIO,
    S_DECENA,
    S_FALTANTE,
    S_JUNTO_CIFRAS,
    S_RESTO,
    S_UNO_MAS,
    S_UNO_MENOS,
    S_VALOR_POSICIONAL,
)
from app.nucleo.modos import ModosProblema


def _dos_cifras(rng: random.Random, lo: int = 11, hi: int = 98) -> int:
    """Número de dos cifras que no es decena completa."""
    while True:
        n = rng.randint(lo, hi)
        if n % 10:
            return n


class SumemosHasta99(GeneradorNaturales):
    leccion_id = "g1-u07-l01"
    caminos = ("naturales.suma",)
    version = 1

    PROPORCION_FALTANTE = 0.1
    REGLAS = (S_CONFUNDIO, S_RESTO, S_FALTANTE, S_VALOR_POSICIONAL, S_UNO_MENOS, S_UNO_MAS, S_DECENA,
              S_JUNTO_CIFRAS, S_COPIO)

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        while True:
            tipo = rng.choice(("D0+D0", "DU+U", "DU+D0", "DU+DU"))
            if tipo == "D0+D0":
                a, b = rng.randint(1, 8) * 10, rng.randint(1, 8) * 10
            elif tipo == "DU+U":
                a, b = _dos_cifras(rng), rng.randint(1, 9)
            elif tipo == "DU+D0":
                a, b = _dos_cifras(rng), rng.randint(1, 8) * 10
            else:
                a, b = _dos_cifras(rng), _dos_cifras(rng)
            if rng.random() < 0.5:
                a, b = b, a
            if a + b <= 99 and not lleva(a, b):
                break
        forma = FALTANTE if rng.random() < self.PROPORCION_FALTANTE else CALCULO
        return Planteo([a, b], [SUMA], forma=forma)

    def rango_ok(self, datos) -> bool:
        a, b = datos["numeros"]
        return (datos["operaciones"] == [SUMA] and a >= 1 and b >= 1 and max(a, b) >= 10
                and a + b <= 99 and not lleva(a, b))
