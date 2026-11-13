"""
g1-u04-l03 "Contemos de forma progresiva y regresiva" (1.º grado, unidad 4).

Panamáticas 1.º, clases 3.1 a 3.4: contar de 2 en 2 y de 5 en 5, en orden progresivo y
regresivo, hasta 20. Contar de 1 en 1 hacia adelante y hacia atrás está en U4 L2 (clase 2.2).
Fuera por ahora: números pares e impares (clase 3.3), que es clasificar, no contar.

- De 2 en 2 (55 %): números pares del 0 al 20, 5 términos.
- De 5 en 5 (45 %): 0, 5, 10, 15, 20, con 4 o 5 términos.
- Regresiva en un 40 %. Un hueco (80 %) o dos, nunca en el primer término.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    SECUENCIA,
    GeneradorNumeracion,
    huecos_secuencia,
    secuencia,
    terminos,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import REGLAS_SECUENCIA, UNO_MAS, UNO_MENOS

MAXIMO = 20


def secuencia_en_rango(rng: random.Random, paso: int, largo: int, *, maximo: int, regresiva: float,
                       multiplo: int) -> tuple[int, int]:
    """(inicio, salto) de una secuencia de `largo` términos entre 0 y `maximo`, con términos
    múltiplos de `multiplo`."""
    tramo = paso * (largo - 1)
    candidatos = [x for x in range(0, maximo - tramo + 1) if x % multiplo == 0]
    menor = rng.choice(candidatos)
    if rng.random() < regresiva:
        return menor + tramo, -paso
    return menor, paso


class ContarDe2YDe5(GeneradorNumeracion):
    leccion_id = "g1-u04-l03"
    version = 1
    FORMAS = {"de_2": 0.55, "de_5": 0.45}
    PROPORCION_REGRESIVA = 0.4
    REGLAS = (*REGLAS_SECUENCIA, UNO_MENOS, UNO_MAS)

    def _secuencia(self, rng, paso, largo):
        inicio, salto = secuencia_en_rango(rng, paso, largo, maximo=MAXIMO,
                                           regresiva=self.PROPORCION_REGRESIVA, multiplo=paso)
        return secuencia(inicio, salto, largo, huecos_secuencia(rng, largo))

    def forma_de_2(self, rng: random.Random):
        return self._secuencia(rng, 2, 5)

    def forma_de_5(self, rng: random.Random):
        return self._secuencia(rng, 5, rng.randint(4, 5))

    def rango_ok(self, datos, forma):
        if forma != SECUENCIA or abs(datos["salto"]) not in (2, 5):
            return False
        ts = terminos(datos)
        return all(0 <= t <= MAXIMO and t % abs(datos["salto"]) == 0 for t in ts)
