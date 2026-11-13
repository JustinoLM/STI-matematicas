"""
Reglas de error del camino naturales.numeracion (1.º grado, fase 5b).

Cada regla lee los datos del problema (numeracion.py: forma y números) y el hueco, y devuelve las
respuestas que daría un estudiante con ese error. Como en reglas.py, cada lección arma su lista
con las que le aplican y el orden es la prioridad.

Familias (con ejemplos de Panamáticas 1.º, unidades 2, 4 y 6, y de la guía del docente):
- contar: uno de más o de menos (contar rápido sin señalar uno a uno), solo la primera fila de
  5, solo las sueltas (16 → 6), las barras como unidades (4 barras y 8 → 12), los grupos en vez
  del número (7 barras → 7);
- leer y escribir: cifras invertidas (31 por 13), cifras separadas ("cuarenta y ocho" → 408),
  confundir el 6 con el 9;
- decenas: confundir decenas con unidades (53 → 3 decenas y 5 unidades), descomponer por cifras
  (64 → 6 y 4), una decena de más o de menos, un cero de más (7 grupos de 10 → 700);
- secuencias: seguir de 1 en 1, ir en sentido contrario, saltarse un número, no cambiar la
  decena al cruzarla (39, _ → 30);
- semirrecta: contar las marcas desde la decena de la derecha (57 → 53), la decena vecina;
- comparar: el símbolo al revés, comparar solo las unidades (45 _ 54 → >), marcar igual;
- ordenar: al revés, por la cifra de las unidades, dos vecinos cambiados.

Para "formar" (`3 y 4 forman _`) se usan las reglas de naturales.suma con el camino de
numeración (con_camino): son las mismas funciones, con otro código.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Optional, Sequence

from app.nucleo.errores import ReglaError
from app.nucleo.lecciones.naturales import reglas as suma
from app.nucleo.lecciones.naturales.numeracion import (
    CAMINO,
    COMPARAR,
    COMPONER,
    CONTAR,
    DECENAS,
    DESCOMPONER,
    FORMAR,
    FORMAR_FALTANTE,
    GRUPOS,
    HUECO_DECENA,
    HUECO_DECENAS,
    HUECO_FALTANTE,
    HUECO_FLECHA,
    HUECO_ORDEN,
    HUECO_RELACION,
    HUECO_RESULTADO,
    HUECO_UNIDAD,
    HUECO_UNIDADES,
    LEER,
    NOMBRE,
    OPCION_IGUAL,
    OPCION_MAYOR,
    OPCION_MENOR,
    ORDENAR,
    SECUENCIA,
    UBICAR,
    indice_termino,
    invertir,
    relacion,
)


class _C:
    """Datos del problema que leen las reglas."""

    def __init__(self, p: Any, hueco_id: str):
        self.p = p
        self.d = p.datos
        self.forma = self.d["forma"]
        self.hueco = hueco_id

    @property
    def correcta(self) -> Any:
        """Valor correcto del hueco (int; id de opción; en ubicar, el número buscado)."""
        if self.forma == UBICAR:
            return self.d["n"]
        h = self.p.huecos[self.hueco]
        return int(h.correcta) if hasattr(h, "banco") else h.correcta

    @property
    def n(self) -> int:
        return self.d["n"]

    @property
    def salto(self) -> int:
        return self.d["salto"]


TERMINOS = "termino*"


def _aplica(huecos: Optional[Sequence[str]], hueco_id: str) -> bool:
    if huecos is None:
        return True
    return hueco_id in huecos or (TERMINOS in huecos and indice_termino(hueco_id) is not None)


def _regla(nombre: str, descripcion: str, formas: Sequence[str], huecos: Optional[Sequence[str]],
           fn: Callable[[_C], list]) -> ReglaError:
    """Regla de numeración. En ubicar, `fn` da números y la regla responde con las flechas que
    los señalan; en ordenar, `fn` da listas completas."""
    def candidatos(p, hueco_id: str):
        forma = p.datos.get("forma")
        if forma not in formas or not _aplica(huecos, hueco_id):
            return []
        if forma == ORDENAR:
            return fn(_C(p, hueco_id)) if hueco_id == HUECO_ORDEN else []
        if hueco_id not in p.huecos:
            return []
        c = _C(p, hueco_id)
        valores = fn(c)
        if forma == UBICAR:
            return [letra for letra, v in p.datos["flechas"].items() if v in valores and v != c.n]
        return [x if isinstance(x, str) else Decimal(x) for x in valores if isinstance(x, str) or x >= 0]
    return ReglaError(f"{CAMINO}.{nombre}", descripcion, candidatos)


def con_camino(regla: ReglaError, nombre: str, formas: Sequence[str] = (FORMAR, FORMAR_FALTANTE)) -> ReglaError:
    """La misma regla de naturales.suma con el camino de numeración, solo en esas formas."""
    def candidatos(p, hueco_id: str):
        if p.datos.get("forma") not in formas:
            return []
        return regla.candidatos(p, hueco_id)
    return ReglaError(f"{CAMINO}.{nombre}", regla.descripcion, candidatos)


def _cambiar_6_y_9(n: int) -> list[int]:
    t = str(n)
    if "6" not in t and "9" not in t:
        return []
    return [int(t.translate(str.maketrans("69", "96")))]


def _espejo_decena(n: int) -> list[int]:
    """57 → 53: contó las marcas desde la decena de la derecha."""
    u = n % 10
    if u in (0, 5):
        return []
    return [n // 10 * 10 + (10 - u)]


def _rel_unidades(a: int, b: int) -> list[str]:
    """Comparó solo las unidades (45 _ 54 → >), si eso cambia la respuesta."""
    if a // 10 == b // 10:
        return []
    r = relacion(a % 10, b % 10)
    return [r] if r != relacion(a, b) else []


def _al_reves(r: str) -> list[str]:
    return {OPCION_MENOR.id: [OPCION_MAYOR.id], OPCION_MAYOR.id: [OPCION_MENOR.id]}.get(r, [])


def _correcto_orden(c: _C) -> list[int]:
    return sorted(c.d["numeros"], reverse=not c.d["ascendente"])


def _dec(xs: Sequence[int]) -> list[Decimal]:
    return [Decimal(x) for x in xs]


def _por_unidades(c: _C) -> list[list[Decimal]]:
    orden = sorted(c.d["numeros"], key=lambda x: (x % 10, x), reverse=not c.d["ascendente"])
    return [_dec(orden)] if orden != _correcto_orden(c) else []


def _vecinos(c: _C) -> list[list[Decimal]]:
    bien = _correcto_orden(c)
    salida = []
    for i in range(len(bien) - 1):
        x = list(bien)
        x[i], x[i + 1] = x[i + 1], x[i]
        salida.append(_dec(x))
    return salida


_R, _F = HUECO_RESULTADO, HUECO_FALTANTE
_NUM = (CONTAR, NOMBRE, FORMAR, FORMAR_FALTANTE, SECUENCIA, LEER, DECENAS, DESCOMPONER)

# ─── Contar, leer y escribir ─────────────────────────────────────────────────

def _unidad_de_conteo(c: _C) -> bool:
    """¿El hueco se cuenta de 1 en 1? (no el total de grupos de 10 ni la decena completa)"""
    return not ((c.forma == GRUPOS and not c.d["faltante"]) or c.hueco == HUECO_DECENA)


UNO_MAS = _regla("conto_uno_mas", "Contó uno de más", (*_NUM, GRUPOS), None,
                 lambda c: [c.correcta + 1] if _unidad_de_conteo(c) else [])
UNO_MENOS = _regla("conto_uno_menos", "Contó uno de menos", (*_NUM, GRUPOS), None,
                   lambda c: [c.correcta - 1] if _unidad_de_conteo(c) else [])
UNA_FILA = _regla("conto_solo_una_fila", "Contó solo la primera fila de 5", (CONTAR,), (_R,),
                  lambda c: [5] if 5 < c.n <= 10 else [])
SOLO_UNIDADES = _regla("solo_las_unidades", "Escribió solo las unidades (las sueltas)",
                       (CONTAR, NOMBRE, COMPONER), (_R,),
                       lambda c: [c.n % 10] if c.n > 10 and c.n % 10 else [])
BARRAS_COMO_UNIDADES = _regla("conto_las_barras_como_unidades",
                              "Contó cada barra de 10 como si fuera 1", (CONTAR, COMPONER), (_R,),
                              lambda c: [c.n // 10 + c.n % 10] if c.n > 10 else [])
ESCRIBIO_GRUPOS = _regla("escribio_los_grupos", "Escribió cuántos grupos de 10 hay en vez del número",
                         (CONTAR, GRUPOS), (_R,),
                         lambda c: ([c.d["grupos"]] if c.forma == GRUPOS else
                                    [c.n // 10] if c.n >= 20 and c.n % 10 == 0 else []))
CERO_DE_MAS = _regla("cero_de_mas", "Agregó un cero de más", (GRUPOS,), (_R,),
                     lambda c: [100 * c.d["grupos"]])
ESCRIBIO_EL_TOTAL = _regla("escribio_el_total", "Escribió el número completo en vez de una parte",
                           (GRUPOS, DESCOMPONER), (_F, HUECO_DECENA, HUECO_UNIDAD),
                           lambda c: [10 * c.d["grupos"]] if c.forma == GRUPOS else [c.n])
DECENA_DE_MAS = _regla("decena_de_mas", "Se equivocó en una decena (10 de más)",
                       (CONTAR, NOMBRE, GRUPOS, COMPONER, LEER, UBICAR, DESCOMPONER), (_R, HUECO_DECENA, HUECO_FLECHA),
                       lambda c: [c.correcta + 10] if c.correcta >= 10 else [])
DECENA_DE_MENOS = _regla("decena_de_menos", "Se equivocó en una decena (10 de menos)",
                         (CONTAR, NOMBRE, GRUPOS, COMPONER, LEER, UBICAR, DESCOMPONER), (_R, HUECO_DECENA, HUECO_FLECHA),
                         lambda c: [c.correcta - 10] if c.correcta >= 20 else [])
INVIRTIO = _regla("invirtio_cifras", "Invirtió las cifras (31 por 13)", (CONTAR, NOMBRE, LEER, UBICAR, SECUENCIA),
                  (_R, HUECO_FLECHA, TERMINOS),
                  lambda c: [x] if (x := invertir(c.correcta)) is not None else [])
CIFRAS_SEPARADAS = _regla("escribio_cifras_separadas",
                          "Escribió las cifras por separado (cuarenta y ocho → 408)", (NOMBRE, COMPONER), (_R,),
                          lambda c: [int(f"{c.n // 10 * 10}{c.n % 10}")] if c.n > 20 and c.n % 10 else [])
SEIS_Y_NUEVE = _regla("confundio_6_y_9", "Confundió el 6 con el 9", (NOMBRE, CONTAR), (_R,),
                      lambda c: _cambiar_6_y_9(c.n))

# ─── Decenas y unidades ──────────────────────────────────────────────────────

CONFUNDIO_DU = _regla("confundio_decenas_unidades", "Confundió las decenas con las unidades",
                      (DECENAS, COMPONER), (HUECO_DECENAS, HUECO_UNIDADES, _R),
                      lambda c: ({HUECO_DECENAS: [c.n % 10], HUECO_UNIDADES: [c.n // 10]}.get(c.hueco, [])
                                 if c.forma == DECENAS else
                                 [x] if (x := invertir(c.n)) is not None else []))
DECENA_COMPLETA = _regla("escribio_la_decena_completa", "Escribió el valor de las decenas (50) en vez de cuántas (5)",
                         (DECENAS,), (HUECO_DECENAS,), lambda c: [c.n // 10 * 10] if c.n >= 20 else [])
POR_CIFRAS = _regla("descompuso_por_cifras", "Descompuso por cifras (64 → 6 y 4, no 60 y 4)",
                    (DESCOMPONER,), (HUECO_DECENA,), lambda c: [c.n // 10])

# ─── Secuencias ──────────────────────────────────────────────────────────────

def _signo(x: int) -> int:
    return 1 if x > 0 else -1


def _sin_cambiar_decena(c: _C) -> list[int]:
    previo = c.correcta - c.salto
    if previo // 10 == c.correcta // 10 or abs(c.salto) >= 10:
        return []
    return [previo // 10 * 10 + c.correcta % 10]


DE_UNO_EN_UNO = _regla("siguio_de_uno_en_uno", "Siguió de 1 en 1 en vez de saltar", (SECUENCIA,), (TERMINOS,),
                       lambda c: [c.correcta - c.salto + _signo(c.salto)] if abs(c.salto) > 1 else [])
SENTIDO_CONTRARIO = _regla("sentido_contrario", "Contó en el sentido contrario", (SECUENCIA,), (TERMINOS,),
                           lambda c: [c.correcta - 2 * c.salto])
SE_SALTO = _regla("se_salto_un_numero", "Se saltó un número de la secuencia", (SECUENCIA,), (TERMINOS,),
                  lambda c: [c.correcta + c.salto])
NO_CAMBIO_DECENA = _regla("no_cambio_la_decena", "Al cruzar la decena no la cambió (39, 30)",
                          (SECUENCIA,), (TERMINOS,), _sin_cambiar_decena)

# ─── Semirrecta ──────────────────────────────────────────────────────────────

ESPEJO = _regla("conto_desde_la_otra_decena", "Contó las marcas desde la decena de la derecha (57 → 53)",
                (LEER, UBICAR), (_R, HUECO_FLECHA), lambda c: _espejo_decena(c.correcta))

# ─── Comparar ────────────────────────────────────────────────────────────────

COMPARO_UNIDADES = _regla("comparo_las_unidades", "Comparó solo las unidades", (COMPARAR,), (HUECO_RELACION,),
                          lambda c: _rel_unidades(c.d["a"], c.d["b"]))
SIMBOLO_AL_REVES = _regla("simbolo_al_reves", "Usó el símbolo al revés (< por >)", (COMPARAR,), (HUECO_RELACION,),
                          lambda c: _al_reves(c.correcta))
MARCO_IGUAL = _regla("marco_igual", "Marcó igual con números distintos", (COMPARAR,), (HUECO_RELACION,),
                     lambda c: [OPCION_IGUAL.id] if c.correcta != OPCION_IGUAL.id else [])
NO_VIO_IGUALES = _regla("no_vio_que_son_iguales", "No vio que los números son iguales", (COMPARAR,),
                        (HUECO_RELACION,),
                        lambda c: [OPCION_MENOR.id, OPCION_MAYOR.id] if c.correcta == OPCION_IGUAL.id else [])

# ─── Ordenar ─────────────────────────────────────────────────────────────────

ORDENO_AL_REVES = _regla("ordeno_al_reves", "Ordenó al revés (de mayor a menor o de menor a mayor)",
                         (ORDENAR,), (HUECO_ORDEN,), lambda c: [_dec(_correcto_orden(c)[::-1])])
ORDENO_POR_UNIDADES = _regla("ordeno_por_las_unidades", "Ordenó por la cifra de las unidades",
                             (ORDENAR,), (HUECO_ORDEN,), _por_unidades)
CAMBIO_VECINOS = _regla("cambio_dos_vecinos", "Dejó dos números vecinos en el orden contrario",
                        (ORDENAR,), (HUECO_ORDEN,), _vecinos)

# ─── Formar (reglas de suma con el camino de numeración) ─────────────────────

FORMAR_FALTANTE_R = con_camino(suma.S_FALTANTE, "faltante")
FORMAR_COPIO = con_camino(suma.S_COPIO, "copio_un_numero")
FORMAR_RESTO = con_camino(suma.S_RESTO, "resto")
FORMAR_JUNTO = con_camino(suma.S_JUNTO_CIFRAS, "junto_cifras")
FORMAR_VALOR_POSICIONAL = con_camino(suma.S_VALOR_POSICIONAL, "valor_posicional")

# ─── Listas por forma ────────────────────────────────────────────────────────

REGLAS_CONTAR = (UNA_FILA, SOLO_UNIDADES, BARRAS_COMO_UNIDADES, ESCRIBIO_GRUPOS, INVIRTIO, UNO_MENOS, UNO_MAS,
                 DECENA_DE_MENOS, DECENA_DE_MAS)
REGLAS_SECUENCIA = (DE_UNO_EN_UNO, SENTIDO_CONTRARIO, SE_SALTO, NO_CAMBIO_DECENA)
REGLAS_COMPARAR = (COMPARO_UNIDADES, SIMBOLO_AL_REVES, MARCO_IGUAL, NO_VIO_IGUALES)
REGLAS_ORDENAR = (ORDENO_AL_REVES, ORDENO_POR_UNIDADES, CAMBIO_VECINOS)
REGLAS_FORMAR = (FORMAR_FALTANTE_R, FORMAR_COPIO, FORMAR_RESTO)

# Posiciones erróneas para las flechas de "ubicar": cada una sale de una regla
REGLAS_UBICAR = (INVIRTIO, ESPEJO, DECENA_DE_MENOS, DECENA_DE_MAS)


def posiciones_erroneas(n: int) -> list[int]:
    """Números donde un estudiante con un error típico ubicaría el n (ver REGLAS_UBICAR)."""
    salida = [x for x in (invertir(n), *_espejo_decena(n), n - 10 if n >= 20 else None, n + 10)
              if x is not None]
    return list(dict.fromkeys(salida))
