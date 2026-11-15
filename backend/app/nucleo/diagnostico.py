"""
Diagnóstico inicial del núcleo (fase 7a). Lógica pura.

Recorre el grafo de prerrequisitos del año lectivo para decidir, con pocos problemas, qué lecciones
ya sabe el estudiante:

1. **Lecciones:** las candidatas (habilitadas o asignadas, con generador), en orden del programa.
   Las que ya tiene dominadas (confirmadas) cuentan como sabidas sin probarse.
2. **Qué lección probar:**
   - Al empezar o tras un acierto: la más avanzada de las que quedan sin decidir que no tenga
     sucesores sin decidir.
   - Tras un fallo en L: entre los prerrequisitos de L sin decidir, la que deja más parejo lo que
     queda por debajo y por encima (así retrocede por la mitad y no de una en una).
3. **Cómo se prueba:** `diagnostico_problemas_por_leccion` problemas de un solo intento, sin
   pistas. Todos bien → sabida; todos mal → no sabida; mezcla → hasta
   `diagnostico_problemas_desempate` problemas más y decide la mayoría (empate: no sabida).
4. **Qué se infiere:** sabida → también sus prerrequisitos (transitivos); no sabida → también sus
   sucesores. El cierre pasa por las lecciones no candidatas: si sabe U5 L1, sabe U2 L1 aunque
   U3 L1 no esté habilitada.
5. **Cuándo termina:** sin lecciones por decidir, al llegar a `diagnostico_max_problemas` (no empieza
   una lección que no quepa) o a `diagnostico_max_minutos` de tiempo activo (suma del tiempo de
   cada problema). Lo que quede sin decidir sigue "sin empezar".

El estado no se guarda: se recalcula repitiendo las respuestas en orden (`calcular`). Así, retomar
el diagnóstico otro día es solo volver a llamar a `calcular`.
"""

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.nucleo.parametros import ParametrosNucleo
from app.nucleo.reparto import Grafo

SABIDA = "sabida"
NO_SABIDA = "no_sabida"
SIN_DECIDIR = "sin_decidir"

PROBADA = "probada"
INFERIDA = "inferida"
PREVIA = "previa"           # ya estaba dominada (confirmada) antes del diagnóstico

FIN_COMPLETO = "completo"
FIN_TOPE_PROBLEMAS = "tope_problemas"
FIN_TOPE_TIEMPO = "tope_tiempo"
FIN_SIN_LECCIONES = "sin_lecciones"


@dataclass(frozen=True)
class Respuesta:
    leccion_id: str
    correcto: bool
    tiempo_ms: int = 0


@dataclass(frozen=True)
class Decision:
    decision: str           # SABIDA o NO_SABIDA
    origen: str             # PROBADA, INFERIDA o PREVIA
    aciertos: int = 0
    problemas: int = 0


@dataclass
class EstadoDiagnostico:
    lecciones: list[str]                                     # candidatas, en orden del programa
    decisiones: dict[str, Decision] = field(default_factory=dict)
    siguiente: Optional[str] = None                          # lección del próximo problema
    terminado: bool = False
    motivo_fin: Optional[str] = None
    problemas: int = 0
    tiempo_ms: int = 0

    @property
    def sin_decidir(self) -> list[str]:
        return [lec for lec in self.lecciones if lec not in self.decisiones]

    @property
    def sabidas(self) -> list[str]:
        return [lec for lec in self.lecciones if lec in self.decisiones and self.decisiones[lec].decision == SABIDA]

    def avance(self, p: ParametrosNucleo) -> float:
        """Entre 0 y 1, para una barra sin conteos."""
        if self.terminado or not self.lecciones:
            return 1.0
        decididas = len(self.decisiones) / len(self.lecciones)
        return round(min(1.0, max(decididas, self.problemas / p.diagnostico_max_problemas)), 3)

    def resultado(self) -> list[dict]:
        """Por lección, en orden del programa (para guardar y mostrar al profesor)."""
        filas = []
        for lec in self.lecciones:
            d = self.decisiones.get(lec)
            filas.append({
                "leccion_id": lec,
                "decision": d.decision if d else SIN_DECIDIR,
                "origen": d.origen if d else None,
                "aciertos": d.aciertos if d else 0,
                "problemas": d.problemas if d else 0,
            })
        return filas


# ─── Grafo ───────────────────────────────────────────────────────────────────

def ancestros(grafo: Grafo, leccion_id: str) -> set[str]:
    """Prerrequisitos transitivos en todo el grafo (también los no candidatos)."""
    vistos: set[str] = set()
    pila = list(grafo.prerrequisitos.get(leccion_id, ()))
    while pila:
        x = pila.pop()
        if x in vistos:
            continue
        vistos.add(x)
        pila.extend(grafo.prerrequisitos.get(x, ()))
    vistos.discard(leccion_id)
    return vistos


def _cierres(grafo: Grafo, lecciones: Sequence[str]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """(ancestros, descendientes) de cada candidata, restringidos a las candidatas."""
    conjunto = set(lecciones)
    arriba = {lec: ancestros(grafo, lec) & conjunto for lec in lecciones}
    abajo = {lec: {y for y in lecciones if lec in arriba[y]} for lec in lecciones}
    return arriba, abajo


def _elegir(pendientes: set[str], foco: Optional[str], arriba, abajo, orden) -> tuple[str, Optional[str]]:
    """(lección a probar, foco actualizado)."""
    if foco is not None:
        cand = arriba[foco] & pendientes
        if cand:
            # Punto medio: la que deja más parejo lo que queda por debajo y por encima
            x = max(cand, key=lambda y: (min(len(arriba[y] & cand) + 1, len(abajo[y] & cand) + 1), orden(y)))
            return x, foco
    sumideros = [y for y in pendientes if not (abajo[y] & pendientes)]
    return max(sumideros, key=orden), None


def _decidir(resultados: list[bool], p: ParametrosNucleo) -> Optional[str]:
    """SABIDA, NO_SABIDA o None si todavía faltan problemas."""
    n = len(resultados)
    aciertos = sum(resultados)
    if n < p.diagnostico_problemas_por_leccion:
        return None
    if n == p.diagnostico_problemas_por_leccion and aciertos in (0, n):
        return SABIDA if aciertos == n else NO_SABIDA
    if n < p.diagnostico_problemas_por_leccion + p.diagnostico_problemas_desempate:
        return None
    return SABIDA if aciertos * 2 > n else NO_SABIDA


# ─── Cálculo ─────────────────────────────────────────────────────────────────

def calcular(
    lecciones: Sequence[str],
    conocidas: set[str],
    grafo: Grafo,
    respuestas: Sequence[Respuesta],
    p: ParametrosNucleo,
) -> EstadoDiagnostico:
    """Repite las respuestas en orden y devuelve el estado: decisiones, la lección del próximo
    problema o, si terminó, el motivo."""
    lecciones = grafo.ordenar(lecciones)
    pos = {lec: i for i, lec in enumerate(lecciones)}
    estado = EstadoDiagnostico(lecciones=list(lecciones))
    if not lecciones:
        estado.terminado, estado.motivo_fin = True, FIN_SIN_LECCIONES
        return estado
    arriba, abajo = _cierres(grafo, lecciones)
    for lec in lecciones:
        if lec in conocidas:
            estado.decisiones[lec] = Decision(SABIDA, PREVIA)

    def orden(lec: str):
        return (grafo.orden.get(lec, 0), pos[lec])

    def marcar(lec: str, decision: str, resultados: list[bool]) -> None:
        estado.decisiones[lec] = Decision(decision, PROBADA, sum(resultados), len(resultados))
        inferidas = arriba[lec] if decision == SABIDA else abajo[lec]
        for y in inferidas:
            if y not in estado.decisiones:
                estado.decisiones[y] = Decision(decision, INFERIDA)

    foco: Optional[str] = None
    actual: Optional[str] = None
    resultados: list[bool] = []
    max_ms = p.diagnostico_max_minutos * 60_000
    pendientes_resp = list(respuestas)

    while True:
        pendientes = set(estado.sin_decidir)
        if not pendientes:
            estado.terminado, estado.motivo_fin = True, FIN_COMPLETO
            break
        if estado.tiempo_ms >= max_ms:
            estado.terminado, estado.motivo_fin = True, FIN_TOPE_TIEMPO
            break
        if actual is None or actual not in pendientes:
            actual, resultados = None, []
            if estado.problemas + p.diagnostico_problemas_por_leccion > p.diagnostico_max_problemas:
                estado.terminado, estado.motivo_fin = True, FIN_TOPE_PROBLEMAS
                break
            actual, foco = _elegir(pendientes, foco, arriba, abajo, orden)
        elif estado.problemas >= p.diagnostico_max_problemas:
            # El desempate no cabe: la lección queda sin decidir
            estado.terminado, estado.motivo_fin = True, FIN_TOPE_PROBLEMAS
            break

        if not pendientes_resp:
            estado.siguiente = actual
            break
        r = pendientes_resp.pop(0)
        estado.problemas += 1
        estado.tiempo_ms += max(r.tiempo_ms, 0)
        # Manda la lección guardada en el problema (por si el grafo cambió a mitad)
        if r.leccion_id != actual:
            actual, resultados = r.leccion_id, []
            if actual not in pendientes:
                actual = None
                continue
        resultados.append(r.correcto)
        decision = _decidir(resultados, p)
        if decision is not None:
            marcar(actual, decision, resultados)
            if decision == NO_SABIDA:
                foco = actual
            actual, resultados = None, []
    return estado
