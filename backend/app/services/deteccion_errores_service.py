"""
Service para detección de tipos de error.

Analiza respuestas incorrectas y clasifica el error cometido. Se invoca en cada
intento incorrecto de una práctica (PracticeService) y su resultado se guarda en
`estudiante_error` y alimenta el prompt de la pista de nivel 3.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

from app.models.hints import TipoError
from app.models.problem import Operacion, Problema

TOLERANCIA = Decimal("0.01")

DESCRIPCIONES = {
    TipoError.DESALINEACION_DECIMALES: "No alineaste correctamente los puntos decimales",
    TipoError.PUNTO_MAL_COLOCADO: "El punto decimal está en la posición incorrecta",
    TipoError.CONFUNDIO_OPERACION: "Usaste una operación diferente a la solicitada",
    TipoError.ORDEN_INCORRECTO: "El orden de los números afecta el resultado",
    TipoError.ERROR_TABLA: "Revisa las tablas de multiplicar",
    TipoError.ERROR_CALCULO_GENERAL: "Hubo un error en el cálculo",
}


def _dec(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _cerca(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCIA


def _digitos(valor: Decimal) -> str:
    """Dígitos significativos sin punto ni ceros sobrantes: 2.50 → '25', 0.025 → '25'."""
    texto = format(valor.normalize(), "f").replace("-", "").replace(".", "")
    return texto.strip("0") or "0"


class DeteccionErroresService:
    """Service para detectar tipos de error."""

    @staticmethod
    def detectar_tipo_error(problema: Problema, respuesta_estudiante) -> TipoError:
        """
        Analiza la respuesta incorrecta y detecta el tipo de error.

        Se evalúan en orden (gana la primera coincidencia):
        1. Confundió la operación (resolvió con otra: p. ej. sumó en vez de restar).
        2. Orden incorrecto (operandos invertidos en resta o división).
        3. Desalineación de decimales (suma/resta operadas como si no hubiera punto).
        4. Punto mal colocado (dígitos correctos, punto en otra posición).
        5. Error de tabla de multiplicar (diferencia de ±un operando).
        6. Error de cálculo general (cualquier otro).
        """
        a = _dec(problema.numero1)
        b = _dec(problema.numero2)
        correcto = _dec(problema.resultado)
        r = _dec(respuesta_estudiante)
        op = problema.operacion

        # 1. Confundió operación
        otras = {
            Operacion.SUMA: [a - b],
            Operacion.RESTA: [a + b],
            Operacion.MULTIPLICACION: [a + b],
            Operacion.DIVISION: [a * b],
        }.get(op, [])
        if any(_cerca(r, x) for x in otras):
            return TipoError.CONFUNDIO_OPERACION

        # 2. Orden incorrecto
        if op == Operacion.RESTA and _cerca(r, b - a):
            return TipoError.ORDEN_INCORRECTO
        if op == Operacion.DIVISION and a != 0 and _cerca(r, b / a):
            return TipoError.ORDEN_INCORRECTO

        # 3. Desalineación de decimales (suma/resta): operó como si no hubiera punto
        tiene_decimales = a != a.to_integral_value() or b != b.to_integral_value()
        if tiene_decimales and op in (Operacion.SUMA, Operacion.RESTA):
            sin_punto = DeteccionErroresService._calcular_sin_decimales(a, b, op)
            if sin_punto is not None and _cerca(r, sin_punto):
                return TipoError.DESALINEACION_DECIMALES

        # 4. Punto mal colocado: mismos dígitos que el resultado, punto en otra posición
        #    (en multiplicación y división incluye "olvidó el punto": 1.2 × 3 = 36)
        if tiene_decimales and _digitos(r) == _digitos(correcto) and not _cerca(r, correcto):
            return TipoError.PUNTO_MAL_COLOCADO

        # 5. Error en tabla de multiplicar (operandos enteros)
        if op == Operacion.MULTIPLICACION and not tiene_decimales:
            diff = abs(r - correcto)
            if diff in (a, b):
                return TipoError.ERROR_TABLA

        # 6. Error de cálculo general
        return TipoError.ERROR_CALCULO_GENERAL

    @staticmethod
    def _calcular_sin_decimales(a: Decimal, b: Decimal, op: Operacion) -> Optional[Decimal]:
        """Calcula como si los números fueran enteros (quitando el punto de cada uno)."""
        try:
            x = Decimal(_digitos_con_ceros(a))
            y = Decimal(_digitos_con_ceros(b))
        except InvalidOperation:
            return None
        if op == Operacion.SUMA:
            return x + y
        if op == Operacion.RESTA:
            return x - y
        if op == Operacion.MULTIPLICACION:
            return x * y
        if op == Operacion.DIVISION and y != 0:
            return x / y
        return None

    @staticmethod
    def obtener_descripcion_error(tipo_error: TipoError) -> str:
        """Obtiene descripción amigable del error."""
        return DESCRIPCIONES.get(tipo_error, "Error en el cálculo")


def _digitos_con_ceros(valor: Decimal) -> str:
    """Quita el punto decimal: 12.5 → "125"."""
    texto = format(valor.normalize(), "f")
    return texto.replace(".", "").lstrip("-") or "0"
