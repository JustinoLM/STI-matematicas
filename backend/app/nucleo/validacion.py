"""
Interpretación y validación de las respuestas de cada tipo de hueco.

Las respuestas llegan como JSON: un diccionario {hueco_id: respuesta}. En la forma de ordenar,
{"orden": [números en el orden que dejó el estudiante]}.

| Hueco    | Respuesta aceptada                                  | Correcta si…                         |
|----------|-----------------------------------------------------|--------------------------------------|
| número   | número o texto ("7", "2,5", "2.5")                  | es igual al valor exacto (sin redondear) |
| opción   | id de la opción                                     | es la opción correcta                |
| fracción | {"numerador": 3, "denominador": 4} o "3/4"          | es equivalente (o idéntica, si el hueco no acepta equivalentes) |
| cantidad | {"h": 5, "min": 75} o [5, 75], una por unidad       | coincide en cada unidad (o en total, si acepta sin normalizar) |
| ordenar  | lista con los mismos números                        | quedan en el orden pedido            |

Una respuesta que no tiene la forma esperada (texto que no es número, opción que no existe,
valor que no está en el banco, huecos de más o de menos) lanza RespuestaMalFormada: no es un
error del estudiante sino de quien llama, y no cuenta como intento.

A diferencia del sistema de decimales, no se redondea a 3 decimales: el valor es exacto.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Union

from app.nucleo.problema import (
    Hueco,
    HuecoCantidad,
    HuecoFraccion,
    HuecoNumero,
    HuecoOpcion,
    Problema,
    ProblemaOrdenar,
)

HUECO_ORDEN = "orden"

ValorHueco = Union[Decimal, str, tuple[int, int], tuple[Decimal, ...], list[Decimal]]


class RespuestaMalFormada(ValueError):
    """La respuesta no tiene la forma que exige el hueco."""


@dataclass
class ResultadoHueco:
    hueco_id: str
    valor: Any                      # respuesta interpretada
    correcto: bool
    error: Optional[str] = None     # código de la regla de error (lo pone el generador)


@dataclass
class ResultadoValidacion:
    huecos: dict[str, ResultadoHueco]

    @property
    def correcto(self) -> bool:
        return all(r.correcto for r in self.huecos.values())


# ---------------------------------------------------------------------------
# Interpretación
# ---------------------------------------------------------------------------

def interpretar_numero(crudo: Any) -> Decimal:
    if isinstance(crudo, bool) or crudo is None:
        raise RespuestaMalFormada("Se esperaba un número")
    if isinstance(crudo, (int, Decimal)):
        valor = Decimal(crudo)
    elif isinstance(crudo, float):
        valor = Decimal(str(crudo))
    elif isinstance(crudo, str):
        texto = crudo.strip().replace(",", ".")
        if not texto:
            raise RespuestaMalFormada("Respuesta vacía")
        try:
            valor = Decimal(texto)
        except InvalidOperation:
            raise RespuestaMalFormada(f"'{crudo}' no es un número") from None
    else:
        raise RespuestaMalFormada("Se esperaba un número")
    if not valor.is_finite():
        raise RespuestaMalFormada("Se esperaba un número")
    return valor


def _entero(crudo: Any) -> int:
    if isinstance(crudo, bool):
        raise RespuestaMalFormada("Se esperaba un número entero")
    if isinstance(crudo, int):
        return crudo
    if isinstance(crudo, str) and re.fullmatch(r"-?\d+", crudo.strip()):
        return int(crudo.strip())
    raise RespuestaMalFormada("Se esperaba un número entero")


def interpretar_fraccion(crudo: Any) -> tuple[int, int]:
    if isinstance(crudo, dict):
        if set(crudo) != {"numerador", "denominador"}:
            raise RespuestaMalFormada("La fracción lleva numerador y denominador")
        num, den = _entero(crudo["numerador"]), _entero(crudo["denominador"])
    elif isinstance(crudo, str) and crudo.count("/") == 1:
        a, b = crudo.split("/")
        num, den = _entero(a), _entero(b)
    else:
        raise RespuestaMalFormada("Se esperaba una fracción")
    if den <= 0:
        raise RespuestaMalFormada("El denominador debe ser positivo")
    return num, den


def interpretar_cantidad(hueco: HuecoCantidad, crudo: Any) -> tuple[Decimal, ...]:
    if isinstance(crudo, dict):
        if set(crudo) != set(hueco.unidades):
            raise RespuestaMalFormada(f"Se esperaba un valor para cada unidad: {', '.join(hueco.unidades)}")
        valores = [crudo[u] for u in hueco.unidades]
    elif isinstance(crudo, list):
        if len(crudo) != len(hueco.unidades):
            raise RespuestaMalFormada(f"Se esperaban {len(hueco.unidades)} valores")
        valores = crudo
    else:
        raise RespuestaMalFormada("Se esperaba una cantidad con unidades")
    return tuple(interpretar_numero(v) for v in valores)


def interpretar(hueco: Hueco, crudo: Any) -> ValorHueco:
    """Convierte la respuesta cruda del JSON al valor del tipo de hueco."""
    if isinstance(hueco, HuecoNumero):
        valor = interpretar_numero(crudo)
        if hueco.banco is not None and valor not in {o.valor for o in hueco.banco}:
            raise RespuestaMalFormada("La respuesta no es una de las opciones del banco")
        return valor
    if isinstance(hueco, HuecoOpcion):
        if not isinstance(crudo, str) or crudo not in {o.id for o in hueco.opciones}:
            raise RespuestaMalFormada("La opción elegida no existe")
        return crudo
    if isinstance(hueco, HuecoFraccion):
        return interpretar_fraccion(crudo)
    if isinstance(hueco, HuecoCantidad):
        return interpretar_cantidad(hueco, crudo)
    raise TypeError(f"Hueco desconocido: {hueco!r}")


def interpretar_orden(problema: ProblemaOrdenar, crudo: Any) -> list[Decimal]:
    if not isinstance(crudo, list):
        raise RespuestaMalFormada("Se esperaba la lista de números ordenados")
    valores = [interpretar_numero(v) for v in crudo]
    if sorted(valores) != sorted(problema.numeros):
        raise RespuestaMalFormada("La lista no contiene exactamente los números del problema")
    return valores


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def es_correcta(hueco: Hueco, valor: ValorHueco) -> bool:
    """¿El valor ya interpretado es la respuesta correcta del hueco?"""
    if isinstance(hueco, HuecoNumero):
        return valor == hueco.correcta
    if isinstance(hueco, HuecoOpcion):
        return valor == hueco.correcta
    if isinstance(hueco, HuecoFraccion):
        num, den = valor
        if hueco.acepta_equivalente:
            return num * hueco.denominador == hueco.numerador * den
        return (num, den) == (hueco.numerador, hueco.denominador)
    if isinstance(hueco, HuecoCantidad):
        if tuple(valor) == tuple(hueco.correcta):
            return True
        if hueco.acepta_sin_normalizar:
            total = sum(v * f for v, f in zip(valor, hueco.factores))
            return total == sum(v * f for v, f in zip(hueco.correcta, hueco.factores))
        return False
    raise TypeError(f"Hueco desconocido: {hueco!r}")


def validar(problema: Problema, respuestas: Any) -> ResultadoValidacion:
    """Valida todas las respuestas de un problema. Exige exactamente un valor por hueco."""
    if not isinstance(respuestas, dict):
        raise RespuestaMalFormada("Las respuestas van en un diccionario {hueco: respuesta}")

    if isinstance(problema, ProblemaOrdenar):
        if set(respuestas) != {HUECO_ORDEN}:
            raise RespuestaMalFormada(f"Se esperaba solo la clave '{HUECO_ORDEN}'")
        orden = interpretar_orden(problema, respuestas[HUECO_ORDEN])
        return ResultadoValidacion({
            HUECO_ORDEN: ResultadoHueco(HUECO_ORDEN, orden, orden == problema.correcta)
        })

    faltan = set(problema.huecos) - set(respuestas)
    sobran = set(respuestas) - set(problema.huecos)
    if faltan or sobran:
        raise RespuestaMalFormada(
            f"Huecos sin respuesta: {sorted(faltan)}; desconocidos: {sorted(sobran)}"
        )
    resultados = {}
    for hueco_id, hueco in problema.huecos.items():
        valor = interpretar(hueco, respuestas[hueco_id])
        resultados[hueco_id] = ResultadoHueco(hueco_id, valor, es_correcta(hueco, valor))
    return ResultadoValidacion(resultados)
