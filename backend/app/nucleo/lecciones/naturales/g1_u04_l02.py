"""
g1-u04-l02 "Ordenemos y ubiquemos números en la semirrecta" (1.º grado, unidad 4).

Panamáticas 1.º, clases 2.1 a 2.5: ordenar tarjetas del 1 al 20 de menor a mayor y de mayor a
menor, escribir los números que faltan en la semirrecta del 0 al 20, y comparar números menores
que 20 con <, > e = (clase 2.4: el título de la lección no lo dice, pero el libro lo incluye).

- Ordenar (35 %): de 4 a 6 tarjetas distintas del 0 al 20; de menor a mayor en un 70 %.
- Semirrecta, leer (35 %): del 0 al 20 con todos los números escritos salvo de 1 a 3 seguidos;
  una flecha señala uno de ellos.
- Comparar (30 %): `8 _ 12`; la mitad de las veces un número de una cifra y otro de dos; iguales
  en un 10 %.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    COMPARAR,
    LEER,
    ORDENAR,
    GeneradorNumeracion,
    comparar,
    leer,
    ordenar,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    INVIRTIO,
    REGLAS_COMPARAR,
    REGLAS_ORDENAR,
    UNO_MAS,
    UNO_MENOS,
)

MAXIMO = 20


def par_comparar(rng: random.Random, minimo: int, maximo: int, *, mezcla: float, iguales: float = 0.1):
    """Dos números para comparar: iguales, uno de una cifra y otro de dos, o al azar."""
    if rng.random() < iguales:
        a = rng.randint(minimo, maximo)
        return a, a
    if rng.random() < mezcla:
        a, b = rng.randint(max(minimo, 1), 9), rng.randint(10, maximo)
    else:
        a, b = rng.sample(range(minimo, maximo + 1), 2)
    return (a, b) if rng.random() < 0.5 else (b, a)


class OrdenarYUbicarHasta20(GeneradorNumeracion):
    leccion_id = "g1-u04-l02"
    version = 1
    FORMAS = {ORDENAR: 0.35, LEER: 0.35, COMPARAR: 0.30}
    PROPORCION_ASCENDENTE = 0.7
    REGLAS = (*REGLAS_ORDENAR, *REGLAS_COMPARAR, INVIRTIO, UNO_MENOS, UNO_MAS)

    def forma_ordenar(self, rng: random.Random):
        numeros = rng.sample(range(0, MAXIMO + 1), rng.randint(4, 6))
        return ordenar(numeros, rng.random() < self.PROPORCION_ASCENDENTE)

    def forma_leer(self, rng: random.Random):
        n = rng.randint(1, MAXIMO - 1)
        largo = rng.randint(1, 3)
        primero = rng.randint(max(1, n - largo + 1), min(n, MAXIMO - largo))
        ocultas = list(range(primero, primero + largo))
        return leer(n, desde=0, hasta=MAXIMO, etiquetas_cada=1, ocultas=ocultas)

    def forma_comparar(self, rng: random.Random):
        a, b = par_comparar(rng, 0, MAXIMO, mezcla=0.5)
        return comparar(a, b, con_enunciado=False)

    def rango_ok(self, datos, forma):
        if forma == ORDENAR:
            return 4 <= len(datos["numeros"]) <= 6 and all(0 <= x <= MAXIMO for x in datos["numeros"])
        if forma == LEER:
            return 0 < datos["n"] < MAXIMO and (datos["desde"], datos["hasta"]) == (0, MAXIMO)
        if forma == COMPARAR:
            return 0 <= datos["a"] <= MAXIMO and 0 <= datos["b"] <= MAXIMO
        return False
