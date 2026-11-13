"""
g1-u04-l01 "Conozcamos los números del 11 al 20" (1.º grado, unidad 4).

Panamáticas 1.º, clases 1.1 a 1.3: contar hasta 20 con una decena completa y sueltos ("10 y 6"),
escribir el número que forman 10 y otro ("10 y _ forman 15", en la prueba de la unidad) y unir
cada número con su nombre.

- Contar (50 %): de 11 a 20 íconos, una barra de 10 y los sueltos.
- Formar con el 10 (35 %): `10 y 6 forman _` o `10 y _ forman 17`, mitad y mitad.
- Número desde su nombre (15 %): «catorce» = _.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    CONTAR,
    FORMAR,
    FORMAR_FALTANTE,
    NOMBRE,
    GeneradorNumeracion,
    contar,
    formar,
    nombre,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    BARRAS_COMO_UNIDADES,
    DECENA_DE_MAS,
    DECENA_DE_MENOS,
    FORMAR_COPIO,
    FORMAR_FALTANTE_R,
    FORMAR_JUNTO,
    INVIRTIO,
    SEIS_Y_NUEVE,
    SOLO_UNIDADES,
    UNO_MAS,
    UNO_MENOS,
)


class NumerosHasta20(GeneradorNumeracion):
    leccion_id = "g1-u04-l01"
    version = 1
    admite_iconos = True
    FORMAS = {CONTAR: 0.5, FORMAR: 0.35, NOMBRE: 0.15}
    REGLAS = (SOLO_UNIDADES, BARRAS_COMO_UNIDADES, FORMAR_JUNTO, FORMAR_FALTANTE_R, FORMAR_COPIO, INVIRTIO,
              SEIS_Y_NUEVE, UNO_MENOS, UNO_MAS, DECENA_DE_MENOS, DECENA_DE_MAS)

    def forma_contar(self, rng: random.Random):
        return contar(rng.randint(11, 20))

    def forma_formar(self, rng: random.Random):
        u = rng.randint(1, 10)
        return formar(10, u, falta=1 if rng.random() < 0.5 else None)

    def forma_nombre(self, rng: random.Random):
        return nombre(rng.randint(11, 20))

    def rango_ok(self, datos, forma):
        if forma in (CONTAR, NOMBRE):
            return 11 <= datos["n"] <= 20
        if forma in (FORMAR, FORMAR_FALTANTE):
            # `10 y u forman _` y `10 y _ forman 1u`: el 10 siempre es el primero (el conocido)
            return datos["numeros"][0] == 10 and 1 <= datos["numeros"][1] <= 10
        return False
