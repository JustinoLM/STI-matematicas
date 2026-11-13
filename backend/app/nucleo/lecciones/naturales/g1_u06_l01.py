"""
g1-u06-l01 "Agrupemos y contemos de 10 en 10" (1.º grado, unidad 6).

Panamáticas 1.º, clases 1.1 a 1.4: grupos de 10 elementos, contar de 10 en 10 hasta 90 en orden
progresivo y regresivo, y problemas como "70 lápices, ¿cuántos grupos de 10?" o "3 paquetes de
10 galletas". El libro llega a 90 (9 grupos); el 100 no entra.

- Contar barras de 10 (40 %): de 2 a 9 barras.
- Grupos de 10 (30 %): `7 grupos de 10 son _` o `_ grupos de 10 son 70`, mitad y mitad.
- De 10 en 10 (30 %): 5 términos entre 0 y 90; regresiva en un 40 %.
"""

import random

from app.nucleo.lecciones.naturales.g1_u04_l03 import secuencia_en_rango
from app.nucleo.lecciones.naturales.numeracion import (
    CONTAR,
    GRUPOS,
    SECUENCIA,
    GeneradorNumeracion,
    contar,
    grupos,
    huecos_secuencia,
    secuencia,
    terminos,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    CERO_DE_MAS,
    DE_UNO_EN_UNO,
    DECENA_DE_MAS,
    DECENA_DE_MENOS,
    ESCRIBIO_EL_TOTAL,
    ESCRIBIO_GRUPOS,
    SE_SALTO,
    SENTIDO_CONTRARIO,
    UNO_MAS,
    UNO_MENOS,
)

MAXIMO = 90


class ContarDe10En10(GeneradorNumeracion):
    leccion_id = "g1-u06-l01"
    version = 1
    FORMAS = {CONTAR: 0.4, GRUPOS: 0.3, SECUENCIA: 0.3}
    PROPORCION_REGRESIVA = 0.4
    REGLAS = (ESCRIBIO_GRUPOS, CERO_DE_MAS, ESCRIBIO_EL_TOTAL, DE_UNO_EN_UNO, SENTIDO_CONTRARIO, SE_SALTO,
              DECENA_DE_MENOS, DECENA_DE_MAS, UNO_MENOS, UNO_MAS)

    def forma_contar(self, rng: random.Random):
        return contar(10 * rng.randint(2, 9))

    def forma_grupos(self, rng: random.Random):
        return grupos(rng.randint(1, 9), faltante=rng.random() < 0.5)

    def forma_secuencia(self, rng: random.Random):
        inicio, salto = secuencia_en_rango(rng, 10, 5, maximo=MAXIMO, regresiva=self.PROPORCION_REGRESIVA,
                                           multiplo=10)
        return secuencia(inicio, salto, 5, huecos_secuencia(rng, 5))

    def rango_ok(self, datos, forma):
        if forma == CONTAR:
            return 20 <= datos["n"] <= MAXIMO and datos["n"] % 10 == 0
        if forma == GRUPOS:
            return 1 <= datos["grupos"] <= 9
        if forma == SECUENCIA:
            return abs(datos["salto"]) == 10 and all(0 <= t <= MAXIMO and t % 10 == 0 for t in terminos(datos))
        return False
