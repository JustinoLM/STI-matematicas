"""
El problema genérico: una expresión con huecos tipados, o la forma aparte de ordenar números.

Ejemplos (docs/DISENO_MODULAR.md, sección 1 → Formas de respuesta):

    23 + 14 = _                          Numero, Simbolo, Numero, Simbolo, RefHueco(numero)
    45 _ 54                              Numero, RefHueco(opcion <, >, =), Numero
    17 ÷ 5 = _ residuo _                 ... RefHueco(numero), Texto("residuo"), RefHueco(numero)
    3 h 40 min + 2 h 35 min = _ h _ min  ... RefHueco(cantidad con unidades h, min)
    ½ + ¼ = _/_                          FraccionFija, Simbolo, FraccionFija, Simbolo, RefHueco(fraccion)

El problema se guarda como JSON (problema_a_dict / problema_desde_dict). La vista pública
(incluir_respuestas=False) es la que recibe la pantalla: sin respuestas correctas, sin los
datos internos del generador y sin la regla de error de cada opción del banco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar, Optional, Union

from app.nucleo.modos import ModosProblema

ESQUEMA_VERSION = 1


def texto_numero(valor: Decimal) -> str:
    """Texto de un número sin ceros sobrantes ni notación científica: 5 → "5", 2.50 → "2.5"."""
    if valor == valor.to_integral_value():
        return str(valor.quantize(Decimal(1)))
    return format(valor.normalize(), "f")


def _dec(valor: Any) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


# ---------------------------------------------------------------------------
# Segmentos de la expresión
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Texto:
    """Texto fijo: "decenas y", "residuo", ","."""
    texto: str


@dataclass(frozen=True)
class Numero:
    """Número fijo de la expresión."""
    valor: Decimal


@dataclass(frozen=True)
class FraccionFija:
    """Fracción fija de la expresión: ½."""
    numerador: int
    denominador: int


@dataclass(frozen=True)
class Simbolo:
    """Operador o relación visible: +, −, ×, ÷, =, <, >."""
    simbolo: str


@dataclass(frozen=True)
class RefHueco:
    """Lugar de la expresión donde va un hueco."""
    hueco_id: str


Segmento = Union[Texto, Numero, FraccionFija, Simbolo, RefHueco]


# ---------------------------------------------------------------------------
# Huecos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Opcion:
    """Opción fija de un hueco de opción: id estable y texto que se muestra."""
    id: str
    texto: str


@dataclass(frozen=True)
class OpcionBanco:
    """Opción del banco de un hueco numérico. `regla` es la regla de error de la que salió
    (None para la correcta y para los números cercanos)."""
    valor: Decimal
    regla: Optional[str] = None

    @property
    def texto(self) -> str:
        return texto_numero(self.valor)


@dataclass
class HuecoNumero:
    id: str
    correcta: Decimal
    banco: Optional[list[OpcionBanco]] = None   # solo en modo banco
    tipo: ClassVar[str] = "numero"


@dataclass
class HuecoOpcion:
    id: str
    opciones: tuple[Opcion, ...]
    correcta: str   # id de la opción
    tipo: ClassVar[str] = "opcion"

    def __post_init__(self):
        ids = [o.id for o in self.opciones]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Hueco {self.id}: opciones repetidas")
        if self.correcta not in ids:
            raise ValueError(f"Hueco {self.id}: la opción correcta no está entre las opciones")


@dataclass
class HuecoFraccion:
    id: str
    numerador: int
    denominador: int
    acepta_equivalente: bool = True   # 2/4 vale por 1/2
    tipo: ClassVar[str] = "fraccion"

    def __post_init__(self):
        if self.denominador <= 0:
            raise ValueError(f"Hueco {self.id}: el denominador debe ser positivo")


@dataclass
class HuecoCantidad:
    """Cantidad con una o varias unidades: `_ h _ min`, `_ m _ cm`.

    `factores` es el valor de cada unidad en la unidad más pequeña (h, min → 60, 1). Solo hace
    falta si se acepta la cantidad sin normalizar (3 h 75 min por 4 h 15 min)."""
    id: str
    unidades: tuple[str, ...]
    correcta: tuple[Decimal, ...]
    factores: Optional[tuple[Decimal, ...]] = None
    acepta_sin_normalizar: bool = False
    tipo: ClassVar[str] = "cantidad"

    def __post_init__(self):
        if not self.unidades or len(self.unidades) != len(self.correcta):
            raise ValueError(f"Hueco {self.id}: una respuesta por unidad")
        if len(set(self.unidades)) != len(self.unidades):
            raise ValueError(f"Hueco {self.id}: unidades repetidas")
        if self.factores is not None and len(self.factores) != len(self.unidades):
            raise ValueError(f"Hueco {self.id}: un factor por unidad")
        if self.acepta_sin_normalizar and self.factores is None:
            raise ValueError(f"Hueco {self.id}: aceptar sin normalizar exige los factores")


Hueco = Union[HuecoNumero, HuecoOpcion, HuecoFraccion, HuecoCantidad]


# ---------------------------------------------------------------------------
# Problemas
# ---------------------------------------------------------------------------

@dataclass
class ProblemaExpresion:
    """Expresión con huecos tipados."""
    leccion_id: str
    generador_version: int
    segmentos: list[Segmento]
    huecos: dict[str, Hueco]            # en el orden en que aparecen
    modos: ModosProblema
    datos: dict[str, Any] = field(default_factory=dict)   # datos internos del generador (JSON)
    iconos: Optional[list[int]] = None  # cuántos íconos lleva cada operando, si se muestran
    # Enunciado con plantilla (1.º y 2.º, sin LLM): {"situacion", "variante", "cantidades"}. La
    # pantalla arma el texto con el tema narrativo del estudiante. Las cantidades son los mismos
    # números del problema (nunca la respuesta) y los íconos salen de ellas.
    enunciado: Optional[dict[str, Any]] = None
    # Presentación especial (por ejemplo {"tipo": "semirrecta", ...}). Es pública: no lleva la
    # respuesta salvo que el ejercicio la muestre (la llegada en "anota la operación").
    presentacion: Optional[dict[str, Any]] = None
    forma: ClassVar[str] = "expresion"

    def __post_init__(self):
        refs = [s.hueco_id for s in self.segmentos if isinstance(s, RefHueco)]
        if len(set(refs)) != len(refs):
            raise ValueError("Un hueco aparece dos veces en la expresión")
        if set(refs) != set(self.huecos):
            raise ValueError("Los huecos de la expresión no coinciden con los huecos definidos")
        for clave, hueco in self.huecos.items():
            if clave != hueco.id:
                raise ValueError(f"Hueco guardado como '{clave}' con id '{hueco.id}'")
        # Los huecos quedan en el orden de la expresión
        self.huecos = {r: self.huecos[r] for r in refs}


@dataclass
class ProblemaOrdenar:
    """Ordenar números arrastrando tarjetas."""
    leccion_id: str
    generador_version: int
    numeros: list[Decimal]               # en el orden en que se muestran
    ascendente: bool
    modos: ModosProblema
    datos: dict[str, Any] = field(default_factory=dict)
    iconos: Optional[list[int]] = None
    forma: ClassVar[str] = "ordenar"

    def __post_init__(self):
        if len(self.numeros) < 2:
            raise ValueError("Hay que ordenar al menos dos números")

    @property
    def correcta(self) -> list[Decimal]:
        return sorted(self.numeros, reverse=not self.ascendente)


Problema = Union[ProblemaExpresion, ProblemaOrdenar]


# ---------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------

def _segmento_a_dict(s: Segmento) -> dict:
    if isinstance(s, Texto):
        return {"tipo": "texto", "texto": s.texto}
    if isinstance(s, Numero):
        return {"tipo": "numero", "valor": texto_numero(s.valor)}
    if isinstance(s, FraccionFija):
        return {"tipo": "fraccion", "numerador": s.numerador, "denominador": s.denominador}
    if isinstance(s, Simbolo):
        return {"tipo": "simbolo", "simbolo": s.simbolo}
    if isinstance(s, RefHueco):
        return {"tipo": "hueco", "hueco_id": s.hueco_id}
    raise TypeError(f"Segmento desconocido: {s!r}")


def _segmento_desde_dict(d: dict) -> Segmento:
    tipo = d["tipo"]
    if tipo == "texto":
        return Texto(d["texto"])
    if tipo == "numero":
        return Numero(_dec(d["valor"]))
    if tipo == "fraccion":
        return FraccionFija(int(d["numerador"]), int(d["denominador"]))
    if tipo == "simbolo":
        return Simbolo(d["simbolo"])
    if tipo == "hueco":
        return RefHueco(d["hueco_id"])
    raise ValueError(f"Segmento desconocido: {tipo}")


def _hueco_a_dict(h: Hueco, incluir_respuestas: bool) -> dict:
    d: dict[str, Any] = {"id": h.id, "tipo": h.tipo}
    if isinstance(h, HuecoNumero):
        if incluir_respuestas:
            d["correcta"] = texto_numero(h.correcta)
        if h.banco is not None:
            d["banco"] = [
                {"valor": o.texto, "regla": o.regla} if incluir_respuestas else {"valor": o.texto}
                for o in h.banco
            ]
    elif isinstance(h, HuecoOpcion):
        d["opciones"] = [{"id": o.id, "texto": o.texto} for o in h.opciones]
        if incluir_respuestas:
            d["correcta"] = h.correcta
    elif isinstance(h, HuecoFraccion):
        if incluir_respuestas:
            d["numerador"] = h.numerador
            d["denominador"] = h.denominador
            d["acepta_equivalente"] = h.acepta_equivalente
    elif isinstance(h, HuecoCantidad):
        d["unidades"] = list(h.unidades)
        if incluir_respuestas:
            d["correcta"] = [texto_numero(v) for v in h.correcta]
            d["factores"] = [texto_numero(f) for f in h.factores] if h.factores else None
            d["acepta_sin_normalizar"] = h.acepta_sin_normalizar
    return d


def _hueco_desde_dict(d: dict) -> Hueco:
    tipo = d["tipo"]
    if tipo == "numero":
        banco = d.get("banco")
        return HuecoNumero(
            id=d["id"],
            correcta=_dec(d["correcta"]),
            banco=[OpcionBanco(_dec(o["valor"]), o.get("regla")) for o in banco] if banco is not None else None,
        )
    if tipo == "opcion":
        return HuecoOpcion(
            id=d["id"],
            opciones=tuple(Opcion(o["id"], o["texto"]) for o in d["opciones"]),
            correcta=d["correcta"],
        )
    if tipo == "fraccion":
        return HuecoFraccion(
            id=d["id"],
            numerador=int(d["numerador"]),
            denominador=int(d["denominador"]),
            acepta_equivalente=bool(d.get("acepta_equivalente", True)),
        )
    if tipo == "cantidad":
        factores = d.get("factores")
        return HuecoCantidad(
            id=d["id"],
            unidades=tuple(d["unidades"]),
            correcta=tuple(_dec(v) for v in d["correcta"]),
            factores=tuple(_dec(f) for f in factores) if factores else None,
            acepta_sin_normalizar=bool(d.get("acepta_sin_normalizar", False)),
        )
    raise ValueError(f"Tipo de hueco desconocido: {tipo}")


def problema_a_dict(p: Problema, incluir_respuestas: bool = True) -> dict:
    """JSON del problema. Con incluir_respuestas=False, la vista pública para la pantalla."""
    d: dict[str, Any] = {
        "esquema": ESQUEMA_VERSION,
        "forma": p.forma,
        "leccion_id": p.leccion_id,
        "generador_version": p.generador_version,
        "modos": p.modos.a_dict(),
        "iconos": list(p.iconos) if p.iconos is not None else None,
    }
    if isinstance(p, ProblemaExpresion):
        d["segmentos"] = [_segmento_a_dict(s) for s in p.segmentos]
        d["huecos"] = [_hueco_a_dict(h, incluir_respuestas) for h in p.huecos.values()]
        d["enunciado"] = p.enunciado
        d["presentacion"] = p.presentacion
    else:
        d["numeros"] = [texto_numero(n) for n in p.numeros]
        d["ascendente"] = p.ascendente
    if incluir_respuestas:
        d["datos"] = p.datos
    return d


def problema_desde_dict(d: dict) -> Problema:
    """Reconstruye un problema guardado con problema_a_dict(incluir_respuestas=True)."""
    if d.get("esquema") != ESQUEMA_VERSION:
        raise ValueError(f"Versión de esquema no admitida: {d.get('esquema')}")
    comunes = dict(
        leccion_id=d["leccion_id"],
        generador_version=int(d["generador_version"]),
        modos=ModosProblema.desde_dict(d["modos"]),
        datos=d.get("datos") or {},
        iconos=list(d["iconos"]) if d.get("iconos") is not None else None,
    )
    if d["forma"] == "expresion":
        huecos = [_hueco_desde_dict(h) for h in d["huecos"]]
        return ProblemaExpresion(
            segmentos=[_segmento_desde_dict(s) for s in d["segmentos"]],
            huecos={h.id: h for h in huecos},
            enunciado=d.get("enunciado"),
            presentacion=d.get("presentacion"),
            **comunes,
        )
    if d["forma"] == "ordenar":
        return ProblemaOrdenar(
            numeros=[_dec(n) for n in d["numeros"]],
            ascendente=bool(d["ascendente"]),
            **comunes,
        )
    raise ValueError(f"Forma de problema desconocida: {d['forma']}")


def solucion(p: Problema) -> dict:
    """Respuesta correcta de cada hueco, con la misma forma en que se envían las respuestas.
    Se muestra al estudiante cuando agota los intentos."""
    if isinstance(p, ProblemaOrdenar):
        return {"orden": [texto_numero(n) for n in p.correcta]}
    sol: dict[str, Any] = {}
    for h in p.huecos.values():
        if isinstance(h, HuecoNumero):
            sol[h.id] = texto_numero(h.correcta)
        elif isinstance(h, HuecoOpcion):
            sol[h.id] = h.correcta
        elif isinstance(h, HuecoFraccion):
            sol[h.id] = {"numerador": h.numerador, "denominador": h.denominador}
        elif isinstance(h, HuecoCantidad):
            sol[h.id] = {u: texto_numero(v) for u, v in zip(h.unidades, h.correcta)}
    return sol
