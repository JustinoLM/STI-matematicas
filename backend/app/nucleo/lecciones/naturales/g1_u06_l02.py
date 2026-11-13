"""
g1-u06-l02 "Conozcamos los números hasta 99" (1.º grado, unidad 6).

Panamáticas 1.º, clases 2.1 a 2.4: contar grupos de 10 y sueltos (4 grupos y 8 más son 48),
representar con barras y cuadros, leer y escribir los números del 21 al 99 y contar de 1 en 1.
La guía advierte dos errores al leer: las cifras por separado ("tres y cinco") y al revés (32
leído "veintitrés").

- Contar (50 %): de 21 a 99, barras de 10 y sueltos.
- De 1 en 1 (30 %): 5 términos que cruzan una decena (`37, 38, _, 40, 41`); el hueco cae en el
  cruce en un 60 %. Regresiva en un 30 %.
- Número desde su nombre (20 %): «cuarenta y ocho» = _.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    CONTAR,
    NOMBRE,
    SECUENCIA,
    GeneradorNumeracion,
    contar,
    nombre,
    secuencia,
    terminos,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    BARRAS_COMO_UNIDADES,
    CIFRAS_SEPARADAS,
    DECENA_DE_MAS,
    DECENA_DE_MENOS,
    INVIRTIO,
    NO_CAMBIO_DECENA,
    SE_SALTO,
    SENTIDO_CONTRARIO,
    SOLO_UNIDADES,
    UNO_MAS,
    UNO_MENOS,
)

LARGO = 5


class NumerosHasta99(GeneradorNumeracion):
    leccion_id = "g1-u06-l02"
    version = 1
    FORMAS = {CONTAR: 0.5, SECUENCIA: 0.3, NOMBRE: 0.2}
    PROPORCION_REGRESIVA = 0.3
    PROPORCION_CRUCE = 0.6
    REGLAS = (BARRAS_COMO_UNIDADES, SOLO_UNIDADES, CIFRAS_SEPARADAS, INVIRTIO, NO_CAMBIO_DECENA, UNO_MENOS,
              UNO_MAS, SENTIDO_CONTRARIO, SE_SALTO, DECENA_DE_MENOS, DECENA_DE_MAS)

    def forma_contar(self, rng: random.Random):
        return contar(rng.randint(21, 99))

    def forma_nombre(self, rng: random.Random):
        return nombre(rng.randint(21, 99))

    def forma_secuencia(self, rng: random.Random):
        # La decena que se cruza (de 30 a 90) y en qué término cae
        decena = 10 * rng.randint(3, 9)
        regresiva = rng.random() < self.PROPORCION_REGRESIVA
        k = rng.randint(1, LARGO - 1)            # el término k es el primero de la decena nueva
        if regresiva:
            inicio, salto = decena - 1 + k, -1   # …, 41, 40 | 39, …: el término k es decena − 1
        else:
            inicio, salto = decena - k, 1        # …, 39 | 40, …: el término k es la decena
        if inicio + salto * (LARGO - 1) > 99:
            inicio -= 1
        hueco = k if rng.random() < self.PROPORCION_CRUCE else rng.choice([i for i in range(1, LARGO) if i != k])
        return secuencia(inicio, salto, LARGO, [hueco])

    def rango_ok(self, datos, forma):
        if forma in (CONTAR, NOMBRE):
            return 21 <= datos["n"] <= 99
        if forma == SECUENCIA:
            ts = terminos(datos)
            return abs(datos["salto"]) == 1 and all(20 <= t <= 99 for t in ts) and len({t // 10 for t in ts}) == 2
        return False
