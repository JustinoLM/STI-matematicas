"""Clasificación del tipo de error de un intento incorrecto."""

from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from app.models.hints import TipoError as T
from app.models.problem import Operacion as O
from app.services.deteccion_errores_service import DeteccionErroresService as S


def _p(op, a, b, r):
    return SimpleNamespace(operacion=op, numero1=D(a), numero2=D(b), resultado=D(r))


@pytest.mark.parametrize(
    "problema,respuesta,esperado",
    [
        (_p(O.RESTA, "9", "4", "5"), "13", T.CONFUNDIO_OPERACION),          # sumó
        (_p(O.SUMA, "9", "4", "13"), "5", T.CONFUNDIO_OPERACION),           # restó
        (_p(O.MULTIPLICACION, "6", "7", "42"), "13", T.CONFUNDIO_OPERACION),
        (_p(O.RESTA, "9", "4", "5"), "-5", T.ORDEN_INCORRECTO),             # invirtió
        (_p(O.DIVISION, "8", "2", "4"), "0.25", T.ORDEN_INCORRECTO),
        (_p(O.SUMA, "1.5", "2.25", "3.75"), "240", T.DESALINEACION_DECIMALES),  # 15 + 225
        (_p(O.MULTIPLICACION, "1.2", "3", "3.6"), "36", T.PUNTO_MAL_COLOCADO),
        (_p(O.MULTIPLICACION, "1.2", "3", "3.6"), "0.36", T.PUNTO_MAL_COLOCADO),
        (_p(O.MULTIPLICACION, "6", "7", "42"), "35", T.ERROR_TABLA),        # 42 − 7
        (_p(O.MULTIPLICACION, "6", "7", "42"), "48", T.ERROR_TABLA),        # 42 + 6
        (_p(O.SUMA, "12", "30", "42"), "50", T.ERROR_CALCULO_GENERAL),
    ],
)
def test_clasificacion(problema, respuesta, esperado):
    assert S.detectar_tipo_error(problema, D(respuesta)) == esperado


def test_acepta_float_y_decimal():
    p = _p(O.RESTA, "9", "4", "5")
    assert S.detectar_tipo_error(p, 13.0) == S.detectar_tipo_error(p, D("13"))


def test_todas_las_categorias_tienen_descripcion():
    for tipo in T:
        assert S.obtener_descripcion_error(tipo)
