"""
Base de "Sumemos y restemos 3 números" (U3 L3 hasta 10 y U5 L4 hasta 20).

Panamáticas 1.º, clases 3.1 a 3.4 (U3) y 4.1 a 4.4 (U5): sumar tres números, restar dos veces,
sumar y restar, restar y sumar. Se resuelve de izquierda a derecha y ningún resultado parcial
pasa del máximo de la lección ni es negativo. Con el signo oculto se ocultan los dos signos y
solo se usan problemas en los que una sola combinación da el resultado.
"""

import random

from app.nucleo.lecciones.naturales.comun import RESTA, SUMA, GeneradorNaturales, Planteo, parciales
from app.nucleo.lecciones.naturales.reglas import REGLAS_TRES_NUMEROS
from app.nucleo.modos import ModosProblema

TIPOS = ((SUMA, SUMA), (RESTA, RESTA), (SUMA, RESTA), (RESTA, SUMA))


class TresNumeros(GeneradorNaturales):
    caminos = ("naturales.suma", "naturales.resta")
    MAXIMO = 10            # de los números y de los resultados parciales
    PRIMERO_MAX = 10
    OTROS_MAX = 9
    REGLAS = REGLAS_TRES_NUMEROS

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:
        ops = list(rng.choice(TIPOS))
        while True:
            nums = [rng.randint(1, self.PRIMERO_MAX), rng.randint(1, self.OTROS_MAX),
                    rng.randint(1, self.OTROS_MAX)]
            if self._dentro(nums, ops):
                return Planteo(nums, ops)

    def _dentro(self, nums, ops) -> bool:
        return all(0 <= x <= self.MAXIMO for x in [*nums, *parciales(nums, ops)])

    def rango_ok(self, datos) -> bool:
        nums, ops = datos["numeros"], datos["operaciones"]
        return len(nums) == 3 and tuple(ops) in TIPOS and self._dentro(nums, ops)
