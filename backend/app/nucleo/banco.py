"""
Banco de opciones para arrastrar (docs/DISENO_MODULAR.md, sección 1 → Formas de respuesta).

- Entre 3 y 4 opciones, todas distintas, una sola correcta, siempre números completos.
- Las incorrectas salen de las reglas de error del camino (se eligen al azar entre las que
  dan valores distintos y válidos). Si no alcanzan, se completa con números cercanos a la
  respuesta correcta (±1, ±2… en pasos de `paso`), nunca inválidos para la lección.
- Cada opción guarda la regla de la que salió: elegirla ya indica el tipo de error.
"""

import random
from decimal import Decimal
from typing import Callable, Optional, Sequence

from app.nucleo.problema import OpcionBanco

MIN_OPCIONES = 3
MAX_OPCIONES = 4
_MAX_PASOS_CERCANOS = 1000


def armar_banco(
    correcta: Decimal,
    distractores: Sequence[tuple[str, Decimal]],
    cantidad: int,
    rng: random.Random,
    es_valido: Callable[[Decimal], bool],
    paso: Decimal = Decimal(1),
) -> list[OpcionBanco]:
    if not MIN_OPCIONES <= cantidad <= MAX_OPCIONES:
        raise ValueError(f"El banco lleva entre {MIN_OPCIONES} y {MAX_OPCIONES} opciones")
    if not es_valido(correcta):
        raise ValueError(f"La respuesta correcta {correcta} no es válida para la lección")

    # Distractores de las reglas: sin repetir valor (gana la primera regla) y válidos
    por_valor: dict[Decimal, str] = {}
    for codigo, valor in distractores:
        if valor != correcta and valor not in por_valor and es_valido(valor):
            por_valor[valor] = codigo
    faltan = cantidad - 1
    elegidos: list[tuple[Decimal, Optional[str]]] = rng.sample(
        list(por_valor.items()), min(faltan, len(por_valor))
    )

    # Números cercanos si las reglas no alcanzan
    usados = {correcta} | {v for v, _ in elegidos}
    k = 1
    while len(elegidos) < faltan:
        if k > _MAX_PASOS_CERCANOS:
            raise ValueError(f"No hay suficientes valores válidos cerca de {correcta}")
        vecinos = [correcta + paso * k, correcta - paso * k]
        rng.shuffle(vecinos)
        for v in vecinos:
            if len(elegidos) < faltan and v not in usados and es_valido(v):
                elegidos.append((v, None))
                usados.add(v)
        k += 1

    opciones = [OpcionBanco(correcta)] + [OpcionBanco(v, regla) for v, regla in elegidos]
    rng.shuffle(opciones)
    return opciones
