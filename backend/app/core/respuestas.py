"""
Regla única de validación de respuestas numéricas.

Una respuesta es correcta si, redondeada a tres decimales (ROUND_HALF_UP), es igual
al resultado almacenado del problema. Todos los puntos del backend que corrigen una
respuesta (práctica, diagnóstico, post-test, regla de tres) usan esta función.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

DECIMALES_RESPUESTA = Decimal("0.001")

Numero = Union[Decimal, int, float, str]


def redondear_respuesta(valor: Numero) -> Decimal:
    """Redondea a tres decimales con ROUND_HALF_UP (mitad hacia arriba)."""
    d = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    return d.quantize(DECIMALES_RESPUESTA, rounding=ROUND_HALF_UP)


def respuesta_es_correcta(respuesta: Numero, resultado: Numero) -> bool:
    """True si la respuesta, redondeada a tres decimales, es igual al resultado almacenado."""
    return redondear_respuesta(respuesta) == redondear_respuesta(resultado)
