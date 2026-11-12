"""
Reglas de error del camino naturales.suma (1.º grado, sin llevar).

Suponen la forma `a + b = _` (hueco "resultado") o, con el signo oculto, `a _ b = c`
(hueco "operador"), con los sumandos en problema.datos["sumandos"].

Orden de prioridad (gana la primera que produce la respuesta): confundir la operación,
restar, contar uno de menos o de más, y escribir uno de los sumandos.

Ejemplo, 3 + 2 = 5: restó → 1, contó uno de menos → 4, contó uno de más → 6, copió un
sumando → 3 o 2.

Las reglas de llevar (2.º grado) se añadirán aquí en la fase 8.
"""

from decimal import Decimal

from app.nucleo.errores import ReglaError
from app.nucleo.problema import Opcion, ProblemaExpresion

HUECO_RESULTADO = "resultado"
HUECO_OPERADOR = "operador"

OPCION_SUMA = Opcion("suma", "+")
OPCION_RESTA = Opcion("resta", "−")
OPCIONES_SUMA_RESTA = (OPCION_SUMA, OPCION_RESTA)


def _sumandos(problema: ProblemaExpresion) -> list[Decimal]:
    return [Decimal(x) for x in problema.datos["sumandos"]]


def _solo_resultado(fn):
    def candidatos(problema: ProblemaExpresion, hueco_id: str):
        return fn(_sumandos(problema)) if hueco_id == HUECO_RESULTADO else []
    return candidatos


CONFUNDIO_OPERACION = ReglaError(
    "naturales.suma.confundio_operacion",
    "Eligió restar cuando había que sumar",
    lambda p, h: [OPCION_RESTA.id] if h == HUECO_OPERADOR else [],
)
RESTO = ReglaError(
    "naturales.suma.resto",
    "Restó los números en vez de sumarlos",
    _solo_resultado(lambda s: [abs(s[0] - s[1])] if len(s) == 2 else []),
)
CONTO_UNO_MENOS = ReglaError(
    "naturales.suma.conto_uno_menos",
    "Contó uno de menos (empezó a contar desde el primer número)",
    _solo_resultado(lambda s: [sum(s) - 1]),
)
CONTO_UNO_MAS = ReglaError(
    "naturales.suma.conto_uno_mas",
    "Contó uno de más",
    _solo_resultado(lambda s: [sum(s) + 1]),
)
COPIO_SUMANDO = ReglaError(
    "naturales.suma.copio_sumando",
    "Escribió uno de los números de la suma",
    _solo_resultado(lambda s: list(s)),
)

REGLAS_SUMA = (CONFUNDIO_OPERACION, RESTO, CONTO_UNO_MENOS, CONTO_UNO_MAS, COPIO_SUMANDO)
