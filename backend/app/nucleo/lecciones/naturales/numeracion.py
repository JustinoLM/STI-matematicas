"""
Lo común a las lecciones de numeración de 1.º grado (fase 5b): U2 L1–L2, U4 L1–L3 y U6 L1–L5.

Panamáticas 1.º, unidades 2, 4 y 6. Cada forma arma su expresión con huecos (o las tarjetas de
ordenar), su enunciado con plantilla y los datos internos que leen las reglas de error
(reglas_numeracion.py). Cada lección elige las formas y sus proporciones (GeneradorNumeracion).

Formas y ejemplos (hueco = _):

| forma          | expresión                         | datos                                  |
|----------------|-----------------------------------|----------------------------------------|
| contar         | íconos del tema · `Hay _`          | n                                      |
| nombre         | "cuarenta y ocho" = _             | n                                      |
| formar         | `3 y 4 forman _`                  | numeros [a, b], operaciones ["+"]      |
| formar_faltante| `2 y _ forman 7`, `_ y 6 forman 6`| numeros [conocido, faltante], ["+"]    |
| secuencia      | `6, 8, _, 12, 14`                 | inicio, salto (con signo), largo       |
| grupos         | `7 grupos de 10 son _`            | grupos, faltante (bool)                |
| decenas        | `53 = _ decenas y _ unidades`     | n                                      |
| componer       | `4 decenas y 3 unidades = _`      | n                                      |
| descomponer    | `77 = _ y _`                      | n                                      |
| comparar       | `45 _ 54` (<, >, =)               | a, b                                   |
| leer           | semirrecta con una flecha · `_`   | n                                      |
| ubicar         | flechas A, B, C · `81 → _`         | n, flechas {letra: valor}              |
| ordenar        | tarjetas para arrastrar            | (ProblemaOrdenar)                      |

"formar" y "formar_faltante" guardan además numeros/operaciones como una suma: así les sirven
las reglas de naturales.suma (faltante, copiar un número, juntar las cifras), con el camino de
numeración (reglas_numeracion.con_camino).

Presentaciones (problema.presentacion, pública):
- {"tipo": "conteo", "cantidades": [n]}: los íconos que se cuentan. A diferencia de los íconos de
  apoyo (modos.mostrar_iconos), son el problema mismo: se dibujan siempre.
- {"tipo": "semirrecta", "ejercicio": "leer" | "ubicar", desde, hasta, marcas_cada,
  etiquetas_cada, flechas: [{"valor", "etiqueta"}], ocultas: [números sin escribir]}. Los
  ejercicios de saltos de la fase 5a no llevan "ejercicio" (vale "saltos").
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Optional, Sequence

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.modos import ModosProblema
from app.nucleo.problema import (
    HuecoNumero,
    HuecoOpcion,
    Numero,
    Opcion,
    Problema,
    ProblemaExpresion,
    ProblemaOrdenar,
    RefHueco,
    Segmento,
    Simbolo,
    Texto,
)

CAMINO = "naturales.numeracion"

# Formas
CONTAR = "contar"
NOMBRE = "nombre"
FORMAR = "formar"
FORMAR_FALTANTE = "formar_faltante"
SECUENCIA = "secuencia"
GRUPOS = "grupos"
DECENAS = "decenas"
COMPONER = "componer"
DESCOMPONER = "descomponer"
COMPARAR = "comparar"
LEER = "leer"
UBICAR = "ubicar"
ORDENAR = "ordenar"

# Huecos
HUECO_RESULTADO = "resultado"
HUECO_FALTANTE = "faltante"
HUECO_DECENAS = "decenas"
HUECO_UNIDADES = "unidades"
HUECO_DECENA = "decena"        # descomponer: la decena completa (70 en 77 = 70 y 7)
HUECO_UNIDAD = "unidad"        # descomponer: las unidades (7)
HUECO_RELACION = "relacion"
HUECO_FLECHA = "flecha"
HUECO_ORDEN = "orden"


def hueco_termino(i: int) -> str:
    return f"termino{i}"


def indice_termino(hueco_id: str) -> Optional[int]:
    return int(hueco_id[len("termino"):]) if hueco_id.startswith("termino") else None


OPCION_MENOR = Opcion("menor", "<")
OPCION_MAYOR = Opcion("mayor", ">")
OPCION_IGUAL = Opcion("igual", "=")
OPCIONES_RELACION = (OPCION_MENOR, OPCION_MAYOR, OPCION_IGUAL)
LETRAS = ("A", "B", "C")


def relacion(a: int, b: int) -> str:
    """Id de la opción correcta para `a _ b`."""
    return OPCION_MENOR.id if a < b else OPCION_MAYOR.id if a > b else OPCION_IGUAL.id


def invertir(n: int) -> Optional[int]:
    """31 → 13. None si no cambia (un dígito, cifras iguales) o termina en 0 (40 → 4)."""
    if n < 10 or n % 10 == 0 or n // 10 == n % 10:
        return None
    return int(str(n)[::-1])


# ---------------------------------------------------------------------------
# Nombres de los números (0 a 99), como en Panamáticas
# ---------------------------------------------------------------------------

_UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
_DIEZ_A_VEINTINUEVE = [
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho",
    "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
    "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta",
            9: "noventa"}


def nombre_numero(n: int) -> str:
    if not 0 <= n <= 99:
        raise ValueError("Solo números del 0 al 99")
    if n < 10:
        return _UNIDADES[n]
    if n < 30:
        return _DIEZ_A_VEINTINUEVE[n - 10]
    d, u = divmod(n, 10)
    return _DECENAS[d] if u == 0 else f"{_DECENAS[d]} y {_UNIDADES[u]}"


# ---------------------------------------------------------------------------
# Planteo
# ---------------------------------------------------------------------------

@dataclass
class PlanteoNum:
    """Lo que arma una forma: la expresión (o las tarjetas), los datos y el enunciado."""
    forma: str
    segmentos: list[Segmento] = field(default_factory=list)
    huecos: dict[str, Any] = field(default_factory=dict)
    datos: dict[str, Any] = field(default_factory=dict)
    situacion: Optional[str] = None            # None: sin enunciado
    cantidades: list[int] = field(default_factory=list)
    iconos: Optional[list[int]] = None         # íconos de apoyo (solo si modos.mostrar_iconos)
    presentacion: Optional[dict[str, Any]] = None
    # Solo la forma de ordenar
    numeros_ordenar: Optional[list[int]] = None
    ascendente: bool = True


def _n(x: int) -> Numero:
    return Numero(Decimal(x))


def _hn(hid: str, correcta: int) -> HuecoNumero:
    return HuecoNumero(hid, Decimal(correcta))


# ─── Formas ──────────────────────────────────────────────────────────────────

def contar(n: int) -> PlanteoNum:
    """Íconos del tema: ¿cuántos hay? Desde 11 se dibujan en barras de 10 y sueltos."""
    return PlanteoNum(
        CONTAR, [Texto("Hay"), RefHueco(HUECO_RESULTADO)], {HUECO_RESULTADO: _hn(HUECO_RESULTADO, n)},
        {"n": n}, situacion="contar", presentacion={"tipo": "conteo", "cantidades": [n]},
    )


def nombre(n: int) -> PlanteoNum:
    """El número escrito con letras: "catorce" = _."""
    return PlanteoNum(
        NOMBRE, [Texto(f"«{nombre_numero(n)}»"), Simbolo("="), RefHueco(HUECO_RESULTADO)],
        {HUECO_RESULTADO: _hn(HUECO_RESULTADO, n)}, {"n": n}, situacion="nombre",
    )


def formar(a: int, b: int, *, falta: Optional[int] = None) -> PlanteoNum:
    """`a y b forman _`; con `falta` = 0 o 1, ese número es el hueco (`_ y 6 forman 6`)."""
    c = a + b
    if falta is None:
        segs = [_n(a), Texto("y"), _n(b), Texto("forman"), RefHueco(HUECO_RESULTADO)]
        return PlanteoNum(FORMAR, segs, {HUECO_RESULTADO: _hn(HUECO_RESULTADO, c)},
                          {"numeros": [a, b], "operaciones": ["+"]}, situacion="formar",
                          cantidades=[a, b], iconos=[a, b])
    conocido, faltante = (b, a) if falta == 0 else (a, b)
    partes: list[Segmento] = [RefHueco(HUECO_FALTANTE), Texto("y"), _n(b)] if falta == 0 else \
        [_n(a), Texto("y"), RefHueco(HUECO_FALTANTE)]
    return PlanteoNum(FORMAR_FALTANTE, [*partes, Texto("forman"), _n(c)],
                      {HUECO_FALTANTE: _hn(HUECO_FALTANTE, faltante)},
                      {"numeros": [conocido, faltante], "operaciones": ["+"], "falta": falta},
                      situacion="formar_faltante", cantidades=[conocido, c], iconos=[conocido])



def secuencia(inicio: int, salto: int, largo: int, huecos_en: Sequence[int]) -> PlanteoNum:
    """`6, 8, _, 12, 14`: `largo` términos desde `inicio`, de `salto` en `salto` (negativo:
    regresiva). Los huecos van en las posiciones `huecos_en` (nunca la primera)."""
    if 0 in huecos_en:
        raise ValueError("El primer término de la secuencia siempre se ve")
    segs: list[Segmento] = []
    huecos: dict[str, Any] = {}
    for i in range(largo):
        t = inicio + salto * i
        if i:
            segs.append(Texto(","))
        if i in huecos_en:
            segs.append(RefHueco(hueco_termino(i)))
            huecos[hueco_termino(i)] = _hn(hueco_termino(i), t)
        else:
            segs.append(_n(t))
    sentido = "progresiva" if salto > 0 else "regresiva"
    return PlanteoNum(SECUENCIA, segs, huecos, {"inicio": inicio, "salto": salto, "largo": largo},
                      situacion=f"secuencia_{sentido}", cantidades=[abs(salto)])


def grupos(g: int, *, faltante: bool) -> PlanteoNum:
    """`7 grupos de 10 son _` o `_ grupos de 10 son 70`."""
    if faltante:
        segs = [RefHueco(HUECO_FALTANTE), Texto("grupos de"), _n(10), Texto("son"), _n(10 * g)]
        huecos = {HUECO_FALTANTE: _hn(HUECO_FALTANTE, g)}
        return PlanteoNum(GRUPOS, segs, huecos, {"grupos": g, "faltante": True},
                          situacion="grupos_cuantos", cantidades=[10 * g])
    segs = [_n(g), Texto("grupos de"), _n(10), Texto("son"), RefHueco(HUECO_RESULTADO)]
    return PlanteoNum(GRUPOS, segs, {HUECO_RESULTADO: _hn(HUECO_RESULTADO, 10 * g)},
                      {"grupos": g, "faltante": False}, situacion="grupos_total", cantidades=[g])


def decenas_y_unidades(n: int) -> PlanteoNum:
    """`53 = _ decenas y _ unidades`."""
    segs = [_n(n), Simbolo("="), RefHueco(HUECO_DECENAS), Texto("decenas y"), RefHueco(HUECO_UNIDADES),
            Texto("unidades")]
    huecos = {HUECO_DECENAS: _hn(HUECO_DECENAS, n // 10), HUECO_UNIDADES: _hn(HUECO_UNIDADES, n % 10)}
    return PlanteoNum(DECENAS, segs, huecos, {"n": n}, situacion="decenas_unidades", cantidades=[n],
                      iconos=[n])


def componer(n: int) -> PlanteoNum:
    """`4 decenas y 3 unidades = _`."""
    d, u = divmod(n, 10)
    segs = [_n(d), Texto("decena y" if d == 1 else "decenas y"), _n(u), Texto("unidad" if u == 1 else "unidades"),
            Simbolo("="), RefHueco(HUECO_RESULTADO)]
    return PlanteoNum(COMPONER, segs, {HUECO_RESULTADO: _hn(HUECO_RESULTADO, n)}, {"n": n},
                      situacion="componer_decenas", cantidades=[d, u])


def descomponer(n: int) -> PlanteoNum:
    """`77 = _ y _` (la decena completa y las unidades, como en el libro: 70 y 7)."""
    segs = [_n(n), Simbolo("="), RefHueco(HUECO_DECENA), Texto("y"), RefHueco(HUECO_UNIDAD)]
    huecos = {HUECO_DECENA: _hn(HUECO_DECENA, n // 10 * 10), HUECO_UNIDAD: _hn(HUECO_UNIDAD, n % 10)}
    return PlanteoNum(DESCOMPONER, segs, huecos, {"n": n}, situacion="descomponer", cantidades=[n],
                      iconos=[n])


def comparar(a: int, b: int, *, con_enunciado: bool) -> PlanteoNum:
    """`45 _ 54` con un hueco de opción <, >, =."""
    segs = [_n(a), RefHueco(HUECO_RELACION), _n(b)]
    huecos = {HUECO_RELACION: HuecoOpcion(HUECO_RELACION, OPCIONES_RELACION, relacion(a, b))}
    return PlanteoNum(COMPARAR, segs, huecos, {"a": a, "b": b},
                      situacion="comparar_cantidades" if con_enunciado else None,
                      cantidades=[a, b] if con_enunciado else [])


def presentacion_puntos(ejercicio: str, *, desde: int, hasta: int, etiquetas_cada: int,
                        flechas: Sequence[tuple[int, Optional[str]]],
                        ocultas: Sequence[int] = ()) -> dict[str, Any]:
    """Semirrecta con flechas que señalan números (leer o ubicar)."""
    if any(not desde <= v <= hasta for v, _ in flechas):
        raise ValueError("Las flechas no caben en el tramo visible")
    return {
        "tipo": "semirrecta",
        "ejercicio": ejercicio,
        "desde": desde,
        "hasta": hasta,
        "marcas_cada": 1,
        "etiquetas_cada": etiquetas_cada,
        "flechas": [{"valor": v, "etiqueta": e} for v, e in flechas],
        "ocultas": sorted(ocultas),
    }


def leer(n: int, *, desde: int, hasta: int, etiquetas_cada: int, ocultas: Sequence[int] = ()) -> PlanteoNum:
    """Una flecha señala una marca sin número: ¿qué número es?"""
    pres = presentacion_puntos(LEER, desde=desde, hasta=hasta, etiquetas_cada=etiquetas_cada,
                               flechas=[(n, None)], ocultas=ocultas)
    return PlanteoNum(LEER, [RefHueco(HUECO_RESULTADO)], {HUECO_RESULTADO: _hn(HUECO_RESULTADO, n)},
                      {"n": n, "desde": desde, "hasta": hasta}, situacion="semirrecta_leer",
                      presentacion=pres)


def ubicar(n: int, distractores: Sequence[int], *, desde: int, hasta: int, etiquetas_cada: int,
           rng: random.Random) -> PlanteoNum:
    """Tres flechas (A, B, C de izquierda a derecha): ¿cuál señala el n? Las incorrectas salen
    de los errores típicos (reglas_numeracion.posiciones_erroneas)."""
    valores = sorted([n, *distractores])
    flechas = {letra: v for letra, v in zip(LETRAS, valores)}
    correcta = next(letra for letra, v in flechas.items() if v == n)
    pres = presentacion_puntos(UBICAR, desde=desde, hasta=hasta, etiquetas_cada=etiquetas_cada,
                               flechas=[(v, letra) for letra, v in flechas.items()])
    opciones = tuple(Opcion(letra, letra) for letra in LETRAS[:len(valores)])
    segs = [_n(n), Simbolo("→"), RefHueco(HUECO_FLECHA)]   # la voz lee "81 está en la flecha ¿cuál?"
    return PlanteoNum(UBICAR, segs, {HUECO_FLECHA: HuecoOpcion(HUECO_FLECHA, opciones, correcta)},
                      {"n": n, "flechas": flechas, "desde": desde, "hasta": hasta},
                      situacion="semirrecta_ubicar", cantidades=[n], presentacion=pres)


def ordenar(numeros: Sequence[int], ascendente: bool) -> PlanteoNum:
    return PlanteoNum(ORDENAR, datos={"numeros": list(numeros), "ascendente": ascendente},
                      situacion="ordenar", numeros_ordenar=list(numeros), ascendente=ascendente)


def ventana_decenas(valores: Sequence[int], *, ancho_minimo: int = 30, maximo: int = 100) -> tuple[int, int]:
    """Tramo de la semirrecta de decena a decena que contiene los valores, sin que ninguno quede
    en el borde y con al menos `ancho_minimo` números."""
    desde = min(valores) // 10 * 10
    hasta = -(-max(valores) // 10) * 10
    if hasta == max(valores) and hasta < maximo:
        hasta += 10
    if desde == min(valores) and desde > 0:
        desde -= 10
    derecha = True   # se amplía alternando a cada lado, para que el número no quede en un extremo
    while hasta - desde < ancho_minimo and (desde > 0 or hasta < maximo):
        if (derecha or desde == 0) and hasta < maximo:
            hasta += 10
        else:
            desde -= 10
        derecha = not derecha
    return desde, hasta


# ---------------------------------------------------------------------------
# Base de los generadores de numeración
# ---------------------------------------------------------------------------

Forma = Callable[[random.Random, ModosProblema], PlanteoNum]


class GeneradorNumeracion(GeneradorLeccion):
    """Base de las lecciones de numeración. Cada lección define:

    - FORMAS: {nombre: peso} y un método `forma_<nombre>(rng) → PlanteoNum` por forma;
    - rango_ok(datos, forma) → bool;
    - REGLAS: las reglas de error, en orden de prioridad.
    """

    caminos = (CAMINO,)
    admite_signo_oculto = False
    admite_iconos = False
    FORMAS: dict[str, float] = {}
    REGLAS: tuple = ()

    def plantear(self, rng: random.Random) -> PlanteoNum:
        nombre_forma = rng.choices(list(self.FORMAS), weights=list(self.FORMAS.values()))[0]
        return getattr(self, f"forma_{nombre_forma}")(rng)

    def rango_ok(self, datos: dict[str, Any], forma: str) -> bool:   # pragma: no cover
        """¿Los números están en el rango de la lección? (False para una forma que no tiene)"""
        raise NotImplementedError

    def generar(self, rng: random.Random, modos: ModosProblema) -> Problema:
        return self._armar(self.plantear(rng), modos, rng)

    def _armar(self, pl: PlanteoNum, modos: ModosProblema, rng: random.Random) -> Problema:
        datos = {"forma": pl.forma, **pl.datos}
        enunciado = ({"situacion": pl.situacion, "variante": rng.randrange(1000), "cantidades": pl.cantidades}
                     if pl.situacion else None)
        if pl.forma == ORDENAR:
            return ProblemaOrdenar(
                leccion_id=self.leccion_id, generador_version=self.version,
                numeros=[Decimal(x) for x in pl.numeros_ordenar or []], ascendente=pl.ascendente,
                modos=modos, datos=datos, enunciado=enunciado,
            )
        iconos = pl.iconos if (modos.mostrar_iconos and self.admite_iconos) else None
        return ProblemaExpresion(
            leccion_id=self.leccion_id, generador_version=self.version, segmentos=pl.segmentos,
            huecos=pl.huecos, modos=modos, datos=datos, iconos=iconos, enunciado=enunciado,
            presentacion=pl.presentacion,
        )

    def reglas_error(self):
        return self.REGLAS

    def es_valido(self, valor_: Decimal) -> bool:
        return 0 <= valor_ <= 999 and valor_ == valor_.to_integral_value()

    def en_rango(self, problema: Problema) -> bool:
        d = problema.datos
        forma = d.get("forma")
        if forma is None:
            return False
        if isinstance(problema, ProblemaOrdenar):
            return (forma == ORDENAR and len(set(problema.numeros)) == len(problema.numeros)
                    and self.rango_ok(d, forma))
        return self.rango_ok(d, forma) and _coherente(problema)

    def pista(self, problema: Problema, nivel: int) -> str:
        from app.nucleo.lecciones.naturales.pistas_numeracion import pista_numeracion
        return pista_numeracion(problema, nivel)


def _coherente(p: ProblemaExpresion) -> bool:
    """Las respuestas correctas coinciden con los datos."""
    d, h = p.datos, p.huecos
    forma = d["forma"]

    def num(hid: str) -> int:
        return int(h[hid].correcta)

    if forma in (CONTAR, NOMBRE, LEER):
        return num(HUECO_RESULTADO) == d["n"]
    if forma == FORMAR:
        return num(HUECO_RESULTADO) == sum(d["numeros"])
    if forma == FORMAR_FALTANTE:
        return num(HUECO_FALTANTE) == d["numeros"][1]
    if forma == SECUENCIA:
        return all(num(hid) == d["inicio"] + d["salto"] * indice_termino(hid) for hid in h)
    if forma == GRUPOS:
        return num(HUECO_FALTANTE) == d["grupos"] if d["faltante"] else num(HUECO_RESULTADO) == 10 * d["grupos"]
    if forma == DECENAS:
        return num(HUECO_DECENAS) * 10 + num(HUECO_UNIDADES) == d["n"]
    if forma == COMPONER:
        return num(HUECO_RESULTADO) == d["n"]
    if forma == DESCOMPONER:
        return num(HUECO_DECENA) + num(HUECO_UNIDAD) == d["n"] and num(HUECO_DECENA) % 10 == 0
    if forma == COMPARAR:
        return h[HUECO_RELACION].correcta == relacion(d["a"], d["b"])
    if forma == UBICAR:
        return d["flechas"][h[HUECO_FLECHA].correcta] == d["n"]
    return False


def terminos(datos: dict[str, Any]) -> list[int]:
    """Términos de una secuencia."""
    return [datos["inicio"] + datos["salto"] * i for i in range(datos["largo"])]


def huecos_secuencia(rng: random.Random, largo: int, *, dos: float = 0.2) -> list[int]:
    """Posiciones de los huecos de una secuencia: uno (o dos), nunca el primero."""
    cuantos = 2 if rng.random() < dos else 1
    return sorted(rng.sample(range(1, largo), cuantos))
