"""
g1-u06-l04 "Ubiquemos números en la semirrecta numérica" (1.º grado, unidad 6).

Panamáticas 1.º, clases 4.1 a 4.3: la semirrecta con marcas de 1 en 1 y números de 10 en 10;
escribir el número que señala una flecha, ubicar un número (se descompone: 59 son 50 y 9, desde
el 50 se cuentan 9 marcas) y ordenar números de dos cifras (clase 4.3).

- Leer (45 %): una flecha señala un número que no es decena completa. Tramo de decena a decena
  con al menos 30 números (40 a 70); la semirrecta entera de 0 a 100 en un 20 %.
- Ubicar (35 %): tres flechas, A, B y C: ¿cuál señala el 66? Las otras dos salen de los errores
  típicos (cifras invertidas, contar desde la decena de la derecha, una decena de más o de
  menos); si no alcanzan, un número cercano.
- Ordenar (20 %): 4 o 5 números de dos cifras, a veces con las mismas decenas o las cifras
  invertidas; de menor a mayor en un 60 %.
"""

import random

from app.nucleo.lecciones.naturales.numeracion import (
    LEER,
    ORDENAR,
    UBICAR,
    GeneradorNumeracion,
    invertir,
    leer,
    ordenar,
    ubicar,
    ventana_decenas,
)
from app.nucleo.lecciones.naturales.reglas_numeracion import (
    DECENA_DE_MAS,
    DECENA_DE_MENOS,
    ESPEJO,
    INVIRTIO,
    REGLAS_ORDENAR,
    UNO_MAS,
    UNO_MENOS,
    posiciones_erroneas,
)

SEPARACION_MINIMA = 3   # entre flechas, para que se distingan con el dedo en la tablet


def _separadas(valores) -> bool:
    vs = sorted(valores)
    return all(b - a >= SEPARACION_MINIMA for a, b in zip(vs, vs[1:]))


class UbicarHasta99(GeneradorNumeracion):
    leccion_id = "g1-u06-l04"
    version = 1
    FORMAS = {LEER: 0.45, UBICAR: 0.35, ORDENAR: 0.2}
    PROPORCION_ENTERA = 0.2
    PROPORCION_ASCENDENTE = 0.6
    REGLAS = (ESPEJO, INVIRTIO, DECENA_DE_MENOS, DECENA_DE_MAS, UNO_MENOS, UNO_MAS, *REGLAS_ORDENAR)

    @staticmethod
    def numero(rng: random.Random) -> int:
        return rng.choice([n for n in range(1, 100) if n % 10])

    def forma_leer(self, rng: random.Random):
        n = self.numero(rng)
        desde, hasta = (0, 100) if rng.random() < self.PROPORCION_ENTERA else ventana_decenas([n])
        return leer(n, desde=desde, hasta=hasta, etiquetas_cada=10)

    def forma_ubicar(self, rng: random.Random):
        n = rng.choice([x for x in range(11, 100) if x % 10])
        candidatos = [x for x in posiciones_erroneas(n) if 0 <= x <= 100]
        rng.shuffle(candidatos)
        elegidas: list[int] = []
        for x in candidatos:
            if len(elegidas) < 2 and _separadas([n, *elegidas, x]):
                elegidas.append(x)
        cercanos = [n + k for k in (4, -4, 5, -5, 6, -6) if 0 <= n + k <= 100]
        for x in cercanos:
            if len(elegidas) < 2 and _separadas([n, *elegidas, x]):
                elegidas.append(x)
        desde, hasta = ventana_decenas([n, *elegidas])
        return ubicar(n, elegidas, desde=desde, hasta=hasta, etiquetas_cada=10, rng=rng)

    def forma_ordenar(self, rng: random.Random):
        k = rng.randint(4, 5)
        numeros: set[int] = set()
        base = rng.randint(12, 98)
        if (x := invertir(base)) is not None and rng.random() < 0.5:
            numeros |= {base, x}                       # 37 y 73
        if rng.random() < 0.5:
            d = rng.randint(1, 9) * 10
            numeros |= set(rng.sample(range(d + 1, d + 10), 2))   # misma decena: 45 y 48
        while len(numeros) < k:
            numeros.add(rng.randint(10, 99))
        lista = list(numeros)[:k] if len(numeros) > k else list(numeros)
        rng.shuffle(lista)
        return ordenar(lista, rng.random() < self.PROPORCION_ASCENDENTE)

    def rango_ok(self, datos, forma):
        if forma == LEER:
            return 0 < datos["n"] < 100 and datos["desde"] <= datos["n"] <= datos["hasta"] <= 100
        if forma == UBICAR:
            vs = list(datos["flechas"].values())
            return (len(vs) == 3 and datos["n"] in vs and _separadas(vs)
                    and all(datos["desde"] <= v <= datos["hasta"] for v in vs))
        if forma == ORDENAR:
            return 4 <= len(datos["numeros"]) <= 5 and all(10 <= x <= 99 for x in datos["numeros"])
        return False
