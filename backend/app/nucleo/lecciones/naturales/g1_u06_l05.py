"""
g1-u06-l05 "Comparemos números" (1.º grado, unidad 6).

Panamáticas 1.º, clases 5.1 a 5.4: "mayor que" y "menor que" con < y >, comparar números con
decenas distintas (se mira primero la decena) y con decenas iguales (se comparan las unidades),
y problemas como "25 camisetas rosadas y 34 azules, ¿de cuál hay más?". Fuera: verdadero o falso
con "está entre" y encerrar todos los números mayores que uno dado.

- `45 _ 54` con <, > o =. Decenas iguales en un 40 %, cifras invertidas en un 20 %, iguales en
  un 10 % y uno de una cifra en un 10 %; el resto, decenas distintas.
- Con enunciado (dos personajes y sus objetos) en un 30 %.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    COMPARAR,
    GeneradorNumeracion,
    comparar,
    invertir,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import REGLAS_COMPARAR


class CompararHasta99(GeneradorNumeracion):
    leccion_id = "g1-u06-l05"
    version = 1
    FORMAS = {COMPARAR: 1.0}
    TIPOS = {"misma_decena": 0.4, "invertidas": 0.2, "iguales": 0.1, "una_cifra": 0.1, "distintas": 0.2}
    PROPORCION_ENUNCIADO = 0.3
    REGLAS = REGLAS_COMPARAR

    def par(self, rng: random.Random) -> tuple[int, int]:
        tipo = rng.choices(list(self.TIPOS), weights=list(self.TIPOS.values()))[0]
        if tipo == "misma_decena":
            d = 10 * rng.randint(1, 9)
            a, b = rng.sample(range(d, d + 10), 2)
        elif tipo == "invertidas":
            a = rng.choice([n for n in range(12, 99) if invertir(n) is not None])
            b = invertir(a)
        elif tipo == "iguales":
            a = b = rng.randint(10, 99)
        elif tipo == "una_cifra":
            a, b = rng.randint(1, 9), rng.randint(10, 99)
        else:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            while a // 10 == b // 10:
                b = rng.randint(10, 99)
        return (a, b) if rng.random() < 0.5 else (b, a)

    def forma_comparar(self, rng: random.Random):
        a, b = self.par(rng)
        return comparar(a, b, con_enunciado=rng.random() < self.PROPORCION_ENUNCIADO)

    def rango_ok(self, datos, forma):
        return forma == COMPARAR and 1 <= datos["a"] <= 99 and 1 <= datos["b"] <= 99
