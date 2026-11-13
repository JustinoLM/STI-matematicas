"""
Reglas de error de los caminos naturales.suma y naturales.resta (1.º grado).

Cada regla lee los datos del problema (comun.datos_naturales: números, signos y forma) y el hueco,
y devuelve las respuestas que daría un estudiante con ese error. Se agrupan por familias y cada
lección arma su lista con las que le aplican; el orden de la lista es la prioridad (gana la
primera regla que produce la respuesta).

Familias:
- básicas: confundir la operación, hacer la operación contraria, contar uno de menos o de más,
  copiar un número del problema; con tres números, olvidar el tercero;
- hueco en medio (`a + _ = c`): escribir un número que ya estaba o sumar los que se ven;
- pasos de la estrategia (`9 + 4 = 10 + _ = _`, `13 − 9 = _ + 3 = _`);
- dos cifras: confundir unidades con decenas, juntar las cifras, equivocarse en una decena,
  restar el número menor del mayor en cada columna;
- semirrecta: contar mal los saltos (de 5 en 5 o de 10 en 10) o leerla al revés.

Ejemplos: 3 + 2 → restó 1, contó uno de menos 4, de más 6, copió 3 o 2. 13 − 9 → restó el menor
del mayor 16. 32 + 20 → sumó las decenas como unidades 34. 8 + 5 = 10 + _ → escribió el 5 o el 2.

Las reglas de llevar y pedir prestado en columnas (2.º grado) se añadirán en la fase 8.
"""

from decimal import Decimal
from typing import Callable

from app.nucleo.errores import ReglaError
from app.nucleo.lecciones.naturales.comun import (  # noqa: F401  (se re-exportan)
    ANOTAR,
    FALTANTE,
    HUECO_FALTANTE,
    HUECO_NUMERO1,
    HUECO_NUMERO2,
    HUECO_OPERADOR,
    HUECO_PASO,
    HUECO_RESULTADO,
    OPCION_RESTA,
    OPCION_SUMA,
    OPCIONES_SUMA_RESTA,
    PASOS,
    RESTA,
    SEMIRRECTA,
    SUMA,
    datos_naturales,
    es_hueco_operador,
    indice_operador,
    parciales,
    pide_prestado,
    valor,
)
from app.nucleo.problema import ProblemaExpresion

HUECOS_NUMERICOS = (HUECO_RESULTADO, HUECO_PASO, HUECO_FALTANTE, HUECO_NUMERO1, HUECO_NUMERO2)


class _Ctx:
    """Datos del problema que leen las reglas."""

    def __init__(self, p: ProblemaExpresion, hueco_id: str):
        self.p = p
        self.hueco = hueco_id
        self.nums, self.ops, self.forma = datos_naturales(p)
        self.r = valor(self.nums, self.ops)
        self.dos = len(self.nums) == 2

    @property
    def op(self) -> str:
        """Signo que manda en este hueco: el último para el resultado, el primero en los demás."""
        if es_hueco_operador(self.hueco):
            return self.ops[indice_operador(self.hueco)]
        return self.ops[-1] if self.hueco == HUECO_RESULTADO else self.ops[0]

    @property
    def correcta(self) -> int:
        return int(self.p.huecos[self.hueco].correcta)

    @property
    def salto(self) -> int:
        return int(self.p.datos.get("salto", 1))


Candidatos = Callable[[_Ctx], list]


def _regla(codigo: str, descripcion: str, op, huecos: tuple[str, ...], fn: Candidatos) -> ReglaError:
    """Regla que solo responde en esos huecos y cuando el signo que manda es `op` (None: la
    regla decide sola, por ejemplo al cambiar uno de los signos de tres números)."""
    def candidatos(p: ProblemaExpresion, hueco_id: str):
        if hueco_id not in huecos and not (HUECO_OPERADOR in huecos and es_hueco_operador(hueco_id)):
            return []
        if hueco_id not in p.huecos:
            return []
        c = _Ctx(p, hueco_id)
        if op is not None and c.op != op:
            return []
        return [x if isinstance(x, str) else Decimal(x) for x in fn(c) if isinstance(x, str) or x >= 0]
    return ReglaError(codigo, descripcion, candidatos)


def _cambiar_un_signo(c: _Ctx, de: str) -> list[int]:
    """Resultados de cambiar un signo `de` por el contrario (sin pasar por negativos)."""
    otro = RESTA if de == SUMA else SUMA
    salida = []
    for i, op in enumerate(c.ops):
        if op == de:
            ops = list(c.ops)
            ops[i] = otro
            if all(x >= 0 for x in parciales(c.nums, ops)):
                salida.append(valor(c.nums, ops))
    return salida


def _menor_del_mayor(a: int, b: int) -> list[int]:
    """En cada columna resta la cifra menor de la mayor: 13 − 9 → 16, 82 − 35 → 53."""
    if not pide_prestado(a, b):
        return []
    r, pos = 0, 1
    while a or b:
        r += abs(a % 10 - b % 10) * pos
        a, b, pos = a // 10, b // 10, pos * 10
    return [r]


def _valor_posicional_suma(a: int, b: int) -> list[int]:
    salida = []
    for x, y in ((a, b), (b, a)):
        if y < 10 <= x:
            salida.append(x + 10 * y)          # 32 + 5 → 82: sumó las unidades a las decenas
        if y >= 10 and y % 10 == 0:
            salida.append(x + y // 10)         # 32 + 20 → 34: sumó las decenas como unidades
    return salida


def _valor_posicional_resta(a: int, b: int) -> list[int]:
    salida = []
    if b >= 10 and b % 10 == 0:
        salida.append(a - b // 10)             # 34 − 20 → 32
    if b < 10 <= a:
        salida.append(a - 10 * b)              # 78 − 5 → 28
    return salida


def _junto_cifras(a: int, b: int) -> list[int]:
    """10 + 6 → 106: escribió las cifras una tras otra."""
    if (a < 10) != (b < 10):
        return [int(f"{a}{b}")]
    return []


def _paso_suma(c: _Ctx) -> list[int]:
    a, b = c.nums
    if max(a, b) >= 10:                        # 12 + 3 = 10 + _: escribió un número sin sumar
        dos, uno = (a, b) if a >= 10 else (b, a)
        return [uno, dos - 10]
    _, otro = (a, b) if a >= b else (b, a)
    return [otro]                              # 9 + 4 = 10 + _: escribió el 4 entero


def _paso_resta(c: _Ctx) -> list[int]:
    a, b = c.nums
    u = a - 10
    return [b, u, abs(u - b)]                  # 13 − 9 = _ + 3: escribió 9, 3 o 6


_R, _P, _F, _N1, _N2, _O = (HUECO_RESULTADO, HUECO_PASO, HUECO_FALTANTE, HUECO_NUMERO1, HUECO_NUMERO2,
                            HUECO_OPERADOR)
_NUMERICOS = (_R, _P, _F, _N1, _N2)

# ─── naturales.suma ──────────────────────────────────────────────────────────

S_CONFUNDIO = _regla("naturales.suma.confundio_operacion", "Eligió restar cuando había que sumar",
                     SUMA, (_O,), lambda c: [OPCION_RESTA.id])
S_RESTO = _regla("naturales.suma.resto", "Restó en vez de sumar", None, (_R,),
                 lambda c: ([abs(c.nums[0] - c.nums[1])] if c.ops == [SUMA] else [])
                 if c.dos else _cambiar_un_signo(c, SUMA))
S_OMITIO = _regla("naturales.suma.omitio_tercero", "Sumó solo los dos primeros números", SUMA, (_R,),
                  lambda c: [] if c.dos else [parciales(c.nums, c.ops)[0]])
S_FALTANTE = _regla("naturales.suma.faltante", "Escribió un número que ya estaba o sumó los dos",
                    SUMA, (_F,), lambda c: [c.nums[0], c.r, c.nums[0] + c.r])
S_PASO_SUMANDO = _regla("naturales.suma.paso_sumando",
                        "En el paso escribió un número del problema en vez de lo que sobra",
                        SUMA, (_P,), _paso_suma)
S_PASO_COMPLEMENTO = _regla("naturales.suma.paso_complemento",
                            "En el paso escribió lo que falta para 10 en vez de lo que sobra", SUMA, (_P,),
                            lambda c: [10 - max(c.nums)] if max(c.nums) < 10 else [])
S_SEMIRRECTA_REVES = _regla("naturales.suma.semirrecta_al_reves",
                            "Leyó los saltos al revés (cambió la partida y la llegada)", SUMA, (_N1,),
                            lambda c: [c.r])
S_SALTOS = _regla("naturales.suma.conto_mal_los_saltos", "Contó un salto de más o de menos",
                  SUMA, (_R, _N2), lambda c: [c.correcta - c.salto, c.correcta + c.salto] if c.salto > 1 else [])
S_UNO_MENOS = _regla("naturales.suma.conto_uno_menos",
                     "Contó uno de menos (empezó a contar desde el primer número)",
                     SUMA, _NUMERICOS, lambda c: [c.correcta - 1])
S_UNO_MAS = _regla("naturales.suma.conto_uno_mas", "Contó uno de más", SUMA, _NUMERICOS,
                   lambda c: [c.correcta + 1])
S_COPIO = _regla("naturales.suma.copio_sumando", "Escribió uno de los números de la suma", SUMA, (_R,),
                 lambda c: list(c.nums) if c.dos else [])
S_VALOR_POSICIONAL = _regla("naturales.suma.valor_posicional", "Sumó unidades con decenas", SUMA, (_R,),
                            lambda c: _valor_posicional_suma(*c.nums) if c.dos else [])
S_JUNTO_CIFRAS = _regla("naturales.suma.junto_cifras", "Escribió las cifras una tras otra sin sumar",
                        SUMA, (_R,), lambda c: _junto_cifras(*c.nums) if c.dos and c.forma != PASOS else [])
S_DECENA = _regla("naturales.suma.error_de_decena", "Se equivocó en las decenas (10 de más o de menos)",
                  SUMA, (_R,), lambda c: [c.r - 10, c.r + 10] if c.r >= 10 else [])

# ─── naturales.resta ─────────────────────────────────────────────────────────

R_CONFUNDIO = _regla("naturales.resta.confundio_operacion", "Eligió sumar cuando había que restar",
                     RESTA, (_O,), lambda c: [OPCION_SUMA.id])
R_SUMO = _regla("naturales.resta.sumo", "Sumó en vez de restar", None, (_R,),
                lambda c: ([c.nums[0] + c.nums[1]] if c.ops == [RESTA] else [])
                if c.dos else _cambiar_un_signo(c, RESTA))
R_OMITIO = _regla("naturales.resta.omitio_tercero", "Hizo solo la primera operación", RESTA, (_R,),
                  lambda c: [] if c.dos else [parciales(c.nums, c.ops)[0]])
R_MENOR_DEL_MAYOR = _regla("naturales.resta.menor_del_mayor",
                           "Restó la cifra menor de la mayor en cada columna", RESTA, (_R,),
                           lambda c: _menor_del_mayor(*c.nums) if c.dos else [])
R_FALTANTE = _regla("naturales.resta.faltante", "Escribió un número que ya estaba o sumó los dos",
                    RESTA, (_F,), lambda c: [c.nums[0], c.r, c.nums[0] + c.r])
R_PASO = _regla("naturales.resta.paso_incompleto",
                "En el paso escribió un número del problema en vez de restar", RESTA, (_P,), _paso_resta)
R_SEMIRRECTA_REVES = _regla("naturales.resta.semirrecta_al_reves",
                            "Leyó los saltos al revés (cambió la partida y la llegada)", RESTA, (_N1,),
                            lambda c: [c.r])
R_SALTOS = _regla("naturales.resta.conto_mal_los_saltos", "Contó un salto de más o de menos",
                  RESTA, (_R, _N2), lambda c: [c.correcta - c.salto, c.correcta + c.salto] if c.salto > 1 else [])
R_UNO_MENOS = _regla("naturales.resta.conto_uno_menos", "Quitó uno de menos", RESTA, _NUMERICOS,
                     lambda c: [c.correcta + 1])
R_UNO_MAS = _regla("naturales.resta.conto_uno_mas", "Quitó uno de más", RESTA, _NUMERICOS,
                   lambda c: [c.correcta - 1])
R_COPIO = _regla("naturales.resta.copio_numero", "Escribió uno de los números de la resta", RESTA, (_R,),
                 lambda c: list(c.nums) if c.dos else [])
R_VALOR_POSICIONAL = _regla("naturales.resta.valor_posicional", "Restó unidades con decenas", RESTA, (_R,),
                            lambda c: _valor_posicional_resta(*c.nums) if c.dos else [])
R_DECENA = _regla("naturales.resta.error_de_decena", "Se equivocó en las decenas (10 de más o de menos)",
                  RESTA, (_R,), lambda c: [c.r - 10, c.r + 10] if max(c.nums) >= 10 else [])

# ─── Listas por familia ──────────────────────────────────────────────────────

REGLAS_SUMA = (S_CONFUNDIO, S_RESTO, S_UNO_MENOS, S_UNO_MAS, S_COPIO)
REGLAS_RESTA = (R_CONFUNDIO, R_SUMO, R_UNO_MENOS, R_UNO_MAS, R_COPIO)
REGLAS_TRES_NUMEROS = (S_CONFUNDIO, R_CONFUNDIO, S_OMITIO, R_OMITIO, S_RESTO, R_SUMO,
                       S_UNO_MENOS, S_UNO_MAS, R_UNO_MENOS, R_UNO_MAS)
