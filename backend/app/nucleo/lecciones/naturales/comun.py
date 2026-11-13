"""
Lo común a las lecciones de suma y resta con naturales (1.º grado).

- Operaciones de izquierda a derecha con dos o tres números, y comprobaciones de rango:
  llevar, pedir prestado y cruzar la decena.
- Formas de la expresión (docs/DISENO_MODULAR.md, sección 1 → Formas de respuesta):
  - "calculo":  `a + b = _` o, con el signo oculto, `a _ b = c` (un hueco de opción por signo);
  - "faltante": `a + _ = c` (hueco en medio);
  - "pasos":    la estrategia del libro como huecos, por ejemplo `9 + 4 = 10 + _ = _`;
  - "semirrecta" y "anotar": la presentación especial de la semirrecta (ver semirrecta()).
- GeneradorNaturales: la base de estos generadores. Cada lección solo da su planteo (números,
  signos, forma y situación del enunciado) y su comprobación de rango; la base arma la expresión,
  el enunciado, los íconos, comprueba que el signo oculto no sea ambiguo y da las pistas.

Los datos internos del problema (problema.datos) que leen las reglas de error:
    numeros, operaciones ("+" o "−"), forma, y según la forma: paso (valor del hueco "paso"),
    salto (semirrecta). Los problemas de la versión 1 de g1-u03-l01 guardaban "sumandos"; se
    siguen leyendo.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, Sequence

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.modos import ModosProblema
from app.nucleo.problema import (
    HuecoNumero,
    HuecoOpcion,
    Numero,
    Opcion,
    Problema,
    ProblemaExpresion,
    RefHueco,
    Segmento,
    Simbolo,
)

SUMA = "+"
RESTA = "−"

# Huecos
HUECO_RESULTADO = "resultado"
HUECO_OPERADOR = "operador"
HUECO_PASO = "paso"
HUECO_FALTANTE = "faltante"
HUECO_NUMERO1 = "numero1"
HUECO_NUMERO2 = "numero2"

OPCION_SUMA = Opcion("suma", "+")
OPCION_RESTA = Opcion("resta", "−")
OPCIONES_SUMA_RESTA = (OPCION_SUMA, OPCION_RESTA)
OPCION_DE_SIGNO = {SUMA: OPCION_SUMA.id, RESTA: OPCION_RESTA.id}
SIGNO_DE_OPCION = {v: k for k, v in OPCION_DE_SIGNO.items()}

# Formas
CALCULO = "calculo"
FALTANTE = "faltante"
PASOS = "pasos"
SEMIRRECTA = "semirrecta"   # resolver en la semirrecta: `a + b = _` con los saltos dibujados
ANOTAR = "anotar"           # anotar la operación que muestran los saltos: `_ _ _ = _`


def hueco_operador(i: int) -> str:
    """Id del hueco del signo i (0, 1): "operador", "operador2"."""
    return HUECO_OPERADOR if i == 0 else f"{HUECO_OPERADOR}{i + 1}"


def es_hueco_operador(hueco_id: str) -> bool:
    return hueco_id.startswith(HUECO_OPERADOR)


def indice_operador(hueco_id: str) -> int:
    resto = hueco_id[len(HUECO_OPERADOR):]
    return int(resto) - 1 if resto else 0


# ---------------------------------------------------------------------------
# Aritmética
# ---------------------------------------------------------------------------

def operar(a: int, op: str, b: int) -> int:
    return a + b if op == SUMA else a - b


def parciales(numeros: Sequence[int], operaciones: Sequence[str]) -> list[int]:
    """Resultados de izquierda a derecha: [a∘b, (a∘b)∘c]. El último es el resultado."""
    acc, salida = numeros[0], []
    for op, n in zip(operaciones, numeros[1:]):
        acc = operar(acc, op, n)
        salida.append(acc)
    return salida


def valor(numeros: Sequence[int], operaciones: Sequence[str]) -> int:
    return parciales(numeros, operaciones)[-1]


def lleva(a: int, b: int) -> bool:
    """¿La suma a + b lleva en alguna columna?"""
    while a or b:
        if a % 10 + b % 10 >= 10:
            return True
        a, b = a // 10, b // 10
    return False


def pide_prestado(a: int, b: int) -> bool:
    """¿La resta a − b pide prestado en alguna columna? (a ≥ b)"""
    while b:
        if a % 10 < b % 10:
            return True
        a, b = a // 10, b // 10
    return False


def cruza_decena(a: int, op: str, b: int) -> bool:
    return lleva(a, b) if op == SUMA else pide_prestado(a, b)


def signos_unicos(numeros: Sequence[int], operaciones: Sequence[str]) -> bool:
    """Con el signo oculto, ¿solo una combinación de signos da el resultado sin pasar por
    negativos? (`5 _ 0 = 5` es ambiguo; `5 _ 2 _ 3 = 4` no)."""
    objetivo = valor(numeros, operaciones)
    validas = [
        ops for ops in itertools.product((SUMA, RESTA), repeat=len(operaciones))
        if all(x >= 0 for x in parciales(numeros, ops)) and valor(numeros, ops) == objetivo
    ]
    return validas == [tuple(operaciones)]


def elegir(rng: random.Random, opciones: Sequence[Any], pesos: Optional[Sequence[float]] = None):
    return rng.choices(list(opciones), weights=pesos)[0]


# ---------------------------------------------------------------------------
# Planteo de una lección
# ---------------------------------------------------------------------------

@dataclass
class Planteo:
    """Lo que elige la lección: números, signos, forma y situación del enunciado.

    `situacion` es la situación del enunciado (unir, agregar, quitar, comparar…). Para la forma
    "pasos", `paso` es el valor del hueco del paso y `segmentos_paso` lo que va después del
    primer "=" (con RefHueco(HUECO_PASO) y RefHueco(HUECO_RESULTADO)). Para la semirrecta,
    `presentacion` es la presentación especial."""
    numeros: list[int]
    operaciones: list[str]
    forma: str = CALCULO
    situacion: Optional[str] = None
    paso: Optional[int] = None
    segmentos_paso: Optional[list[Segmento]] = None
    presentacion: Optional[dict[str, Any]] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def resultado(self) -> int:
        return valor(self.numeros, self.operaciones)


def situacion_por_defecto(operaciones: Sequence[str], forma: str, rng: random.Random) -> str:
    if forma == ANOTAR:
        return "anotar_saltos"
    if forma == SEMIRRECTA:
        return "saltos"
    if len(operaciones) > 1:
        return "tres"
    if forma == FALTANTE:
        return "faltante_suma" if operaciones[0] == SUMA else "faltante_resta"
    if operaciones[0] == SUMA:
        return elegir(rng, ("unir", "agregar"))
    return elegir(rng, ("quitar", "quitar", "comparar"))


# ---------------------------------------------------------------------------
# Semirrecta
# ---------------------------------------------------------------------------

def ventana_semirrecta(inicio: int, llegada: int, salto: int, *, minimo: int = 0, maximo: int = 100,
                       ancho_minimo: int = 20) -> tuple[int, int]:
    """Tramo visible: desde la decena anterior al menor hasta la siguiente al mayor, con al menos
    `ancho_minimo` números. Con saltos de 10 se ve la semirrecta entera."""
    if salto >= 10:
        return minimo, maximo
    desde = min(inicio, llegada) // 10 * 10
    hasta = -(-max(inicio, llegada) // 10) * 10
    if hasta == max(inicio, llegada) and hasta < maximo:
        hasta += 10                      # que la llegada o el inicio no quede en el borde
    while hasta - desde < ancho_minimo:
        if desde > minimo:
            desde -= 10
        elif hasta < maximo:
            hasta += 10
        else:
            break
    return max(desde, minimo), min(hasta, maximo)


def semirrecta(inicio: int, op: str, avance: int, salto: int, *, desde: int, hasta: int,
               etiquetas_cada: int, mostrar_llegada: bool) -> dict[str, Any]:
    """Presentación de la semirrecta: el punto de inicio y `avance / salto` saltos de `salto`
    hacia la derecha (suma) o la izquierda (resta). Sin la llegada, salvo que se pida."""
    if avance % salto:
        raise ValueError("El avance debe ser múltiplo del salto")
    llegada = operar(inicio, op, avance)
    if not (desde <= min(inicio, llegada) and max(inicio, llegada) <= hasta):
        raise ValueError("Los saltos no caben en el tramo visible")
    p: dict[str, Any] = {
        "tipo": "semirrecta",
        "desde": desde,
        "hasta": hasta,
        "marcas_cada": 1,
        "etiquetas_cada": etiquetas_cada,
        "inicio": inicio,
        "salto": salto,
        "saltos": avance // salto,
        "sentido": "derecha" if op == SUMA else "izquierda",
    }
    if mostrar_llegada:
        p["llegada"] = llegada
    return p


# ---------------------------------------------------------------------------
# Base de los generadores de suma y resta
# ---------------------------------------------------------------------------

def _dec(n: int) -> Decimal:
    return Decimal(n)


class GeneradorNaturales(GeneradorLeccion):
    """Base de las lecciones de suma y resta con naturales. Cada lección implementa:

    - plantear(rng, modos) → Planteo (números dentro del rango de la lección);
    - rango_ok(datos) → bool (el rango de la lección, para en_rango y las pruebas);
    - REGLAS: la lista de reglas de error, en orden de prioridad.
    """

    admite_signo_oculto = True
    admite_iconos = True
    REGLAS: tuple = ()
    _MAX_REINTENTOS = 200

    # --- Lo propio de cada lección ---

    def plantear(self, rng: random.Random, modos: ModosProblema) -> Planteo:   # pragma: no cover
        raise NotImplementedError

    def rango_ok(self, datos: dict[str, Any]) -> bool:   # pragma: no cover
        raise NotImplementedError

    # --- Generación ---

    def generar(self, rng: random.Random, modos: ModosProblema) -> Problema:
        for _ in range(self._MAX_REINTENTOS):
            pl = self.plantear(rng, modos)
            if not modos.mostrar_signo and pl.forma in (FALTANTE, PASOS):
                # Con el signo oculto solo se pregunta el signo
                pl.forma, pl.paso, pl.segmentos_paso = CALCULO, None, None
            if (not modos.mostrar_signo and pl.forma != ANOTAR
                    and not signos_unicos(pl.numeros, pl.operaciones)):
                continue
            return self._armar(pl, modos, rng)
        raise RuntimeError(f"{self.leccion_id}: no se pudo plantear un problema válido")

    def _armar(self, pl: Planteo, modos: ModosProblema, rng: random.Random) -> ProblemaExpresion:
        nums, ops, r = pl.numeros, pl.operaciones, pl.resultado
        segmentos: list[Segmento] = []
        huecos: dict[str, Any] = {}
        if pl.forma == ANOTAR:
            a, b = nums
            segmentos = [RefHueco(HUECO_NUMERO1), RefHueco(HUECO_OPERADOR), RefHueco(HUECO_NUMERO2),
                         Simbolo("="), RefHueco(HUECO_RESULTADO)]
            huecos = {
                HUECO_NUMERO1: HuecoNumero(HUECO_NUMERO1, _dec(a)),
                HUECO_OPERADOR: HuecoOpcion(HUECO_OPERADOR, OPCIONES_SUMA_RESTA, OPCION_DE_SIGNO[ops[0]]),
                HUECO_NUMERO2: HuecoNumero(HUECO_NUMERO2, _dec(b)),
                HUECO_RESULTADO: HuecoNumero(HUECO_RESULTADO, _dec(r)),
            }
        elif pl.forma == FALTANTE:
            a, b = nums
            segmentos = [Numero(_dec(a)), Simbolo(ops[0]), RefHueco(HUECO_FALTANTE), Simbolo("="), Numero(_dec(r))]
            huecos = {HUECO_FALTANTE: HuecoNumero(HUECO_FALTANTE, _dec(b))}
        elif modos.mostrar_signo:
            segmentos.append(Numero(_dec(nums[0])))
            for op, n in zip(ops, nums[1:]):
                segmentos += [Simbolo(op), Numero(_dec(n))]
            segmentos.append(Simbolo("="))
            if pl.forma == PASOS:
                if pl.paso is None or not pl.segmentos_paso:
                    raise ValueError("La forma de pasos necesita el paso y sus segmentos")
                segmentos += pl.segmentos_paso
                huecos[HUECO_PASO] = HuecoNumero(HUECO_PASO, _dec(pl.paso))
            else:
                segmentos.append(RefHueco(HUECO_RESULTADO))
            huecos[HUECO_RESULTADO] = HuecoNumero(HUECO_RESULTADO, _dec(r))
        else:
            segmentos.append(Numero(_dec(nums[0])))
            for i, (op, n) in enumerate(zip(ops, nums[1:])):
                hid = hueco_operador(i)
                segmentos += [RefHueco(hid), Numero(_dec(n))]
                huecos[hid] = HuecoOpcion(hid, OPCIONES_SUMA_RESTA, OPCION_DE_SIGNO[op])
            segmentos += [Simbolo("="), Numero(_dec(r))]

        datos: dict[str, Any] = {"numeros": list(nums), "operaciones": list(ops), "forma": pl.forma}
        if pl.paso is not None:
            datos["paso"] = pl.paso
        if pl.presentacion is not None:
            datos["salto"] = pl.presentacion["salto"]
        datos.update(pl.extra)

        cantidades = self._cantidades(pl)
        con_iconos = modos.mostrar_iconos and pl.forma not in (SEMIRRECTA, ANOTAR)
        situacion = pl.situacion or situacion_por_defecto(ops, pl.forma, rng)
        enunciado: dict[str, Any] = {"situacion": situacion, "variante": rng.randrange(1000),
                                     "cantidades": cantidades}
        if len(ops) > 1:
            # Con tres números el enunciado cuenta lo que pasa en cada paso (ganar o perder).
            # Con el signo oculto, deducir el signo de la historia es el ejercicio.
            enunciado["acciones"] = ["agregar" if op == SUMA else "quitar" for op in ops]

        return ProblemaExpresion(
            leccion_id=self.leccion_id,
            generador_version=self.version,
            segmentos=segmentos,
            huecos=huecos,
            modos=modos,
            datos=datos,
            iconos=self._iconos(pl) if con_iconos else None,
            enunciado=enunciado,
            presentacion=pl.presentacion,
        )

    @staticmethod
    def _cantidades(pl: Planteo) -> list[int]:
        """Números del enunciado: los del problema que se ven (nunca la respuesta)."""
        if pl.forma == ANOTAR:
            return []
        if pl.forma == FALTANTE:
            return [pl.numeros[0], pl.resultado]     # `a + _ = c`: se ven a y c
        return list(pl.numeros)

    @staticmethod
    def _iconos(pl: Planteo) -> list[int]:
        """Los íconos salen de las mismas cantidades del enunciado: una por número. Con el hueco
        en medio solo se dibuja la parte conocida (dibujar el total daría la respuesta contando)."""
        cantidades = GeneradorNaturales._cantidades(pl)
        return cantidades[:1] if pl.forma == FALTANTE else cantidades

    # --- Reglas, rango y validez ---

    def reglas_error(self):
        return self.REGLAS

    def es_valido(self, valor_: Decimal) -> bool:
        return valor_ >= 0 and valor_ == valor_.to_integral_value()

    def en_rango(self, problema: Problema) -> bool:
        if not isinstance(problema, ProblemaExpresion):
            return False
        d = problema.datos
        nums, ops, forma = d["numeros"], d["operaciones"], d["forma"]
        if len(ops) != len(nums) - 1 or any(x < 0 for x in nums):
            return False
        if any(x < 0 for x in parciales(nums, ops)):
            return False
        if not self.rango_ok(d):
            return False
        return _coherente(problema, nums, ops, forma)

    # --- Pistas ---

    def pista(self, problema: Problema, nivel: int) -> str:
        return pista_naturales(problema, nivel)


def _coherente(p: ProblemaExpresion, nums: list[int], ops: list[str], forma: str) -> bool:
    """La expresión y las respuestas correctas coinciden con los datos."""
    r = valor(nums, ops)
    h = p.huecos
    if forma == ANOTAR:
        return (h[HUECO_NUMERO1].correcta == nums[0] and h[HUECO_NUMERO2].correcta == nums[1]
                and h[HUECO_RESULTADO].correcta == r and h[HUECO_OPERADOR].correcta == OPCION_DE_SIGNO[ops[0]])
    if forma == FALTANTE:
        return h[HUECO_FALTANTE].correcta == nums[1]
    fijos = [s.valor for s in p.segmentos if isinstance(s, Numero)]
    if p.modos.mostrar_signo:
        if fijos[:len(nums)] != nums or h[HUECO_RESULTADO].correcta != r:
            return False
        return forma != PASOS or h[HUECO_PASO].correcta == p.datos["paso"]
    return (fijos == [*nums, r]
            and all(h[hueco_operador(i)].correcta == OPCION_DE_SIGNO[op] for i, op in enumerate(ops)))


# ---------------------------------------------------------------------------
# Pistas
# ---------------------------------------------------------------------------

def datos_naturales(p: ProblemaExpresion) -> tuple[list[int], list[str], str]:
    """(numeros, operaciones, forma), también para los problemas de la versión 1."""
    d = p.datos
    if "numeros" in d:
        return list(d["numeros"]), list(d["operaciones"]), d.get("forma", CALCULO)
    return list(d["sumandos"]), [SUMA], CALCULO


def _contar(desde: int, op: str, cuantos: int) -> str:
    paso = 1 if op == SUMA else -1
    seq = [desde + paso * k for k in range(1, cuantos)]
    return ", ".join(str(n) for n in seq)


def pista_naturales(p: ProblemaExpresion, nivel: int) -> str:
    nums, ops, forma = datos_naturales(p)
    r = valor(nums, ops)
    if not p.modos.mostrar_signo and forma != ANOTAR:
        if len(ops) == 1:
            a, b = nums
            return {
                1: f"Mira el resultado: ¿es más que {a} o menos que {a}?",
                2: (f"{r} es más que {a}. Cuando juntamos o agregamos, tenemos más." if r > a else
                    f"{r} es menos que {a}. Cuando quitamos, tenemos menos."),
                3: (f"Si juntas {a} y {b}, tienes {r}. ¿Qué signo usamos para juntar?" if ops[0] == SUMA else
                    f"Si a {a} le quitas {b}, quedan {r}. ¿Qué signo usamos para quitar?"),
            }[nivel]
        return {
            1: "Prueba los signos uno por uno, de izquierda a derecha.",
            2: f"Empieza con {nums[0]}. ¿Llegas a {r} si sumas o si restas el siguiente número?",
            3: f"Después del primer signo tienes {parciales(nums, ops)[0]}. Ahora busca el segundo signo.",
        }[nivel]

    if forma in (SEMIRRECTA, ANOTAR):
        salto = p.datos.get("salto", 1)
        a, b = nums
        lado = "derecha" if ops[0] == SUMA else "izquierda"
        if forma == ANOTAR:
            return {
                1: "El punto grande es el número de partida. Las flechas son los saltos.",
                2: f"Los saltos van hacia la {lado}: si avanzan sumamos, si retroceden restamos.",
                3: (f"Empieza en {a}. Cuenta cuánto avanzan los saltos, de {salto} en {salto}." if salto > 1 else
                    f"Empieza en {a}. Cuenta los saltos uno por uno."),
            }[nivel]
        return {
            1: f"Pon el dedo en el {a} de la semirrecta.",
            2: (f"Ahora muévete {b} lugares hacia la {lado}, de {salto} en {salto}." if salto > 1 else
                f"Ahora da {b} saltos hacia la {lado}."),
            3: f"Mira el último salto: ¿en qué número cae? Está a la {lado} del {a}.",
        }[nivel]

    if forma == FALTANTE:
        a, b = nums
        if ops[0] == SUMA:
            return {
                1: f"Tienes {a}. ¿Cuántos más necesitas para llegar a {r}?",
                2: f"Cuenta desde {a} hasta {r} con los dedos.",
                3: f"Cuenta desde {a}: {_contar(a, SUMA, r - a + 1) or r}… ¿cuántos números contaste?",
            }[nivel]
        return {
            1: f"Tenías {a} y te quedaron {r}. ¿Cuántos se fueron?",
            2: f"Cuenta hacia atrás desde {a} hasta {r}.",
            3: f"De {r} a {a} hay que contar: {_contar(r, SUMA, a - r + 1) or a}… ¿cuántos son?",
        }[nivel]

    if forma == PASOS:
        a, b = nums
        paso = p.datos["paso"]
        if ops[0] == SUMA:
            if max(a, b) >= 10:
                dos, uno = (a, b) if a >= 10 else (b, a)
                return {
                    1: f"Separa el {dos} en 10 y {dos - 10}.",
                    2: f"Suma los números pequeños: {dos - 10} + {uno}.",
                    3: f"{dos - 10} y {uno} forman {paso}. Ahora junta el 10 y el {paso}.",
                }[nivel]
            grande, otro = (a, b) if a >= b else (b, a)
            falta = 10 - grande
            return {
                1: f"Completa el {grande} hasta 10. ¿Cuánto le falta?",
                2: f"Al {grande} le falta {falta}. Separa el {otro} en {falta} y otro número.",
                3: f"{otro} se separa en {falta} y {otro - falta}. ¿Cuánto es 10 y {otro - falta}?",
            }[nivel]
        unidades = a - 10
        if unidades >= b:
            return {
                1: f"Separa el {a} en 10 y {unidades}.",
                2: f"Quita {b} a las {unidades} unidades.",
                3: f"De {unidades} quitas {b} y quedan {paso}. Junta el 10 y el {paso}.",
            }[nivel]
        return {
            1: f"Separa el {a} en {unidades} y 10.",
            2: f"Quita {b} al 10. ¿Cuánto queda?",
            3: f"De 10 quitas {b} y quedan {paso}. Ahora junta {paso} y {unidades}.",
        }[nivel]

    if len(ops) > 1:
        primero = parciales(nums, ops)[0]
        verbo = {SUMA: "suma", RESTA: "resta"}
        return {
            1: "Resuelve de izquierda a derecha: primero los dos primeros números.",
            2: f"Primero {verbo[ops[0]]}: {nums[0]} {ops[0]} {nums[1]}.",
            3: f"{nums[0]} {ops[0]} {nums[1]} = {primero}. Ahora {verbo[ops[1]]} {nums[2]} a {primero}."
               if ops[1] == SUMA else
               f"{nums[0]} {ops[0]} {nums[1]} = {primero}. Ahora a {primero} le restas {nums[2]}.",
        }[nivel]

    a, b = nums
    if ops[0] == SUMA:
        if a >= 10 or b >= 10:
            return {
                1: "Suma las unidades con las unidades y las decenas con las decenas.",
                2: f"Unidades: {a % 10} + {b % 10}. Decenas: {a // 10} + {b // 10}.",
                3: f"Las unidades dan {a % 10 + b % 10} y las decenas {a // 10 + b // 10}. ¿Qué número forman?"
                   if not lleva(a, b) else f"Empieza en {a} y avanza {b}.",
            }[nivel]
        if nivel == 1:
            return f"Sumar es juntar: junta los {a} y los {b}, y cuenta cuántos hay en total."
        if nivel == 2:
            return f"Empieza en {a} y cuenta {b} más con los dedos."
        intermedios = _contar(a, SUMA, b)
        return (f"Cuenta desde {a}: {intermedios}… ¿qué número sigue?" if intermedios
                else f"¿Qué número viene después del {a}?")
    if a >= 10 and b >= 10:
        return {
            1: "Resta las unidades con las unidades y las decenas con las decenas.",
            2: f"Unidades: {a % 10} − {b % 10}. Decenas: {a // 10} − {b // 10}.",
            3: f"Quedan {a % 10 - b % 10} unidades y {a // 10 - b // 10} decenas. ¿Qué número forman?"
               if not pide_prestado(a, b) else f"Empieza en {a} y retrocede {b}.",
        }[nivel]
    if nivel == 1:
        return f"Restar es quitar: tienes {a} y quitas {b}. ¿Cuántos quedan?"
    if nivel == 2:
        return f"Empieza en {a} y cuenta {b} hacia atrás."
    intermedios = _contar(a, RESTA, b)
    return (f"Cuenta hacia atrás desde {a}: {intermedios}… ¿qué número sigue?" if intermedios
            else f"¿Qué número viene antes del {a}?")


# ---------------------------------------------------------------------------
# Pasos de las estrategias del libro (forma "pasos")
# ---------------------------------------------------------------------------

def _diez() -> Numero:
    return Numero(Decimal(10))


def pasos_completar_10(a: int, b: int) -> tuple[int, list[Segmento]]:
    """Sumemos completando a 10: el sumando mayor se completa a 10 con parte del otro.
    9 + 4 = 10 + _ = _ (paso 3); 2 + 9 = _ + 10 = _ (paso 1)."""
    paso = a + b - 10
    if a >= b:
        return paso, [_diez(), Simbolo(SUMA), RefHueco(HUECO_PASO), Simbolo("="), RefHueco(HUECO_RESULTADO)]
    return paso, [RefHueco(HUECO_PASO), Simbolo(SUMA), _diez(), Simbolo("="), RefHueco(HUECO_RESULTADO)]


def pasos_separar_10(a: int, b: int) -> tuple[int, list[Segmento]]:
    """Sumemos un número de 2 cifras y otro de una cifra: 12 + 3 = 10 + _ = _ (paso 5)."""
    paso = a + b - 10
    return paso, [_diez(), Simbolo(SUMA), RefHueco(HUECO_PASO), Simbolo("="), RefHueco(HUECO_RESULTADO)]


def pasos_resta_hasta_19(a: int, b: int) -> tuple[int, list[Segmento]]:
    """Restemos con números hasta 19.
    Sin cruzar la decena (se resta de las unidades): 19 − 7 = 10 + _ = _ (paso 2).
    Cruzando (se resta del 10): 13 − 9 = _ + 3 = _ (paso 1)."""
    u = a - 10
    if u >= b:
        return u - b, [_diez(), Simbolo(SUMA), RefHueco(HUECO_PASO), Simbolo("="), RefHueco(HUECO_RESULTADO)]
    return 10 - b, [RefHueco(HUECO_PASO), Simbolo(SUMA), Numero(Decimal(u)), Simbolo("="),
                    RefHueco(HUECO_RESULTADO)]
