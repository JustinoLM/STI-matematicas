"""
g1-u02-l01 "Conozcamos los números del 0 al 10" (1.º grado, unidad 2).

Panamáticas 1.º, clases 1.1 a 1.6: contar animales y objetos y escribir cuántos hay, el cero
como "ninguno" y unir cada número con su nombre. Fuera: el trazo de los números.

- Contar (85 %): de 1 a 10 íconos del tema en filas de 5; el 0 (recuadro vacío) en un 10 %.
- Número desde su nombre (15 %): «ocho» = _.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    CONTAR,
    NOMBRE,
    GeneradorNumeracion,
    contar,
    nombre,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    SEIS_Y_NUEVE,
    UNA_FILA,
    UNO_MAS,
    UNO_MENOS,
)


class NumerosHasta10(GeneradorNumeracion):
    leccion_id = "g1-u02-l01"
    version = 1
    FORMAS = {CONTAR: 0.85, NOMBRE: 0.15}
    PROPORCION_CERO = 0.1
    REGLAS = (UNA_FILA, SEIS_Y_NUEVE, UNO_MENOS, UNO_MAS)

    def forma_contar(self, rng: random.Random):
        return contar(0 if rng.random() < self.PROPORCION_CERO else rng.randint(1, 10))

    def forma_nombre(self, rng: random.Random):
        return nombre(rng.randint(0, 10))

    def rango_ok(self, datos, forma):
        return forma in self.FORMAS and 0 <= datos["n"] <= 10
