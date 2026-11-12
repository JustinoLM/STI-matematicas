"""
Reparto de la sesión (docs/DISENO_MODULAR.md, secciones 2 y 3).

Lógica pura: recibe la foto del estudiante y devuelve el plan de la sesión, una lista de
(lección, zona). El servicio arma la foto desde la base.

Candidatas: lecciones habilitadas en el año lectivo del salón más las asignadas solo al
estudiante, siempre que tengan generador. Los prerrequisitos no bloquean una lección que el
profesor habilitó.

Orden de criterios: prioridad del profesor, debilidad, novedad, orden curricular y repaso.

1. **Prioridad.** Las prioritarias que el estudiante aún no domina se reparten
   `fraccion_prioridad` de la sesión (redondeando hacia arriba). Una prioritaria ya dominada
   cede su espacio.
2. **Refuerzo.** Si una lección en progreso "falla" (precisión menor que `umbral_refuerzo` con
   al menos `minimo_resultados_refuerzo` problemas), sus prerrequisitos directos no dominados que
   no son candidatas reciben `problemas_refuerzo` problemas en total.
3. **Extensión.** Los pasos siguientes (sucesores en el grafo) de las candidatas dominadas, que
   no son candidatas, no están dominados ni tienen la extensión en pausa, reciben
   `problemas_extension` problemas en total.
4. **El resto**, entre como máximo `max_lecciones_resto` lecciones: primero las que están en
   progreso, de la más débil a la más fuerte; después las nuevas (no iniciadas cuyos
   prerrequisitos candidatos ya están dominados), como máximo `nuevas_por_sesion`, por orden del
   programa; y al final el repaso (dominadas con repaso pendiente y dominios provisionales), que
   siempre conserva un lugar si lo hay.
5. Si no queda nada para el resto, se da a las prioritarias; si tampoco hay, a las dominadas
   que hace más tiempo que no se practican. Sin ninguna candidata no hay sesión.

Dentro de cada grupo los problemas se reparten por turnos, empezando por la primera lección. Al
final se mezclan, sin empezar por un problema de extensión o de refuerzo.
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Optional, Sequence

from app.models.nucleo import (
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    NO_INICIADO,
    ZONA_EXTENSION,
    ZONA_NORMAL,
    ZONA_PRIORIDAD,
    ZONA_REFUERZO,
    ZONA_REPASO,
)
from app.nucleo.parametros import ParametrosNucleo


class SinLecciones(Exception):
    """El estudiante no tiene ninguna lección para practicar."""


@dataclass(frozen=True)
class Grafo:
    prerrequisitos: dict[str, tuple[str, ...]]
    orden: dict[str, int]

    def sucesores(self, leccion_id: str) -> list[str]:
        return [lec for lec, pres in self.prerrequisitos.items() if leccion_id in pres]

    def ordenar(self, ids: Iterable[str]) -> list[str]:
        return sorted(set(ids), key=lambda i: (self.orden.get(i, math.inf), i))


@dataclass(frozen=True)
class Candidata:
    leccion_id: str
    orden: int
    estado: str = NO_INICIADO
    prioritaria: bool = False
    precision: Optional[float] = None          # en los últimos `ventana_dominio` problemas
    resultados: int = 0                        # cuántos problemas hay en esa ventana
    repaso_pendiente: bool = False
    ultima_practica: Optional[datetime] = None


@dataclass(frozen=True)
class ItemPlan:
    leccion_id: str
    zona: str


# ─── Zonas de extensión y refuerzo ───────────────────────────────────────────

def candidatos_extension(
    candidatas: Sequence[Candidata],
    estados: dict[str, str],
    pausadas: set[str],
    tiene_generador: Callable[[str], bool],
    grafo: Grafo,
) -> list[str]:
    """Pasos siguientes de las candidatas dominadas, por orden del programa."""
    ids_candidatas = {c.leccion_id for c in candidatas}
    sucesores = {
        s
        for c in candidatas if c.estado == DOMINIO_DOMINADO
        for s in grafo.sucesores(c.leccion_id)
    }
    return grafo.ordenar(
        s for s in sucesores
        if s not in ids_candidatas
        and estados.get(s, NO_INICIADO) != DOMINIO_DOMINADO
        and s not in pausadas
        and tiene_generador(s)
    )


def falla(c: Candidata, p: ParametrosNucleo) -> bool:
    return (
        c.estado == DOMINIO_EN_PROGRESO
        and c.resultados >= p.minimo_resultados_refuerzo
        and c.precision is not None
        and c.precision < p.umbral_refuerzo
    )


def candidatos_refuerzo(
    candidatas: Sequence[Candidata],
    estados: dict[str, str],
    tiene_generador: Callable[[str], bool],
    grafo: Grafo,
    p: ParametrosNucleo,
) -> list[str]:
    """Prerrequisitos directos no dominados de las candidatas que fallan, por orden del programa."""
    ids_candidatas = {c.leccion_id for c in candidatas}
    return grafo.ordenar(
        pre
        for c in candidatas if falla(c, p)
        for pre in grafo.prerrequisitos.get(c.leccion_id, ())
        if pre not in ids_candidatas
        and estados.get(pre, NO_INICIADO) != DOMINIO_DOMINADO
        and tiene_generador(pre)
    )


# ─── Reparto ─────────────────────────────────────────────────────────────────

def _por_turnos(ids: Sequence[str], cantidad: int, zona: str) -> list[ItemPlan]:
    if not ids or cantidad <= 0:
        return []
    return [ItemPlan(ids[k % len(ids)], zona) for k in range(cantidad)]


def repartir(
    candidatas: Sequence[Candidata],
    extension: Sequence[str],
    refuerzo: Sequence[str],
    grafo: Grafo,
    p: ParametrosNucleo,
    rng: random.Random,
) -> list[ItemPlan]:
    if not candidatas:
        raise SinLecciones("No hay lecciones habilitadas para practicar.")
    n = p.problemas_por_sesion
    por_orden = sorted(candidatas, key=lambda c: (c.orden, c.leccion_id))

    # 1. Prioridad
    prioritarias = [c.leccion_id for c in por_orden if c.prioritaria and c.estado != DOMINIO_DOMINADO]
    cupo_prioridad = min(n, math.ceil(n * p.fraccion_prioridad)) if prioritarias else 0

    # 2 y 3. Refuerzo y extensión, sin pasarse de lo que queda
    libre = n - cupo_prioridad
    n_refuerzo = min(p.problemas_refuerzo, libre) if refuerzo else 0
    libre -= n_refuerzo
    n_extension = min(p.problemas_extension, libre) if extension else 0
    resto = libre - n_extension

    # 4. El resto
    ids_prioritarias = set(prioritarias)
    generales = [c for c in por_orden if c.leccion_id not in ids_prioritarias]
    en_progreso = sorted(
        (c for c in generales if c.estado == DOMINIO_EN_PROGRESO and not c.repaso_pendiente),
        key=lambda c: (c.precision if c.precision is not None else 0.0, c.orden),
    )
    dominadas = {c.leccion_id for c in candidatas if c.estado == DOMINIO_DOMINADO}
    ids_candidatas = {c.leccion_id for c in candidatas}
    nuevas = [
        c for c in generales
        if c.estado == NO_INICIADO
        and all(pre in dominadas for pre in grafo.prerrequisitos.get(c.leccion_id, ()) if pre in ids_candidatas)
    ][:p.nuevas_por_sesion]
    repaso = [c for c in generales if c.repaso_pendiente]

    principales = [(c.leccion_id, ZONA_NORMAL) for c in en_progreso + nuevas]
    de_repaso = [(c.leccion_id, ZONA_REPASO) for c in repaso]
    if de_repaso:
        elegidas = principales[:p.max_lecciones_resto - 1] + de_repaso
    else:
        elegidas = principales
    elegidas = elegidas[:p.max_lecciones_resto]

    plan: list[ItemPlan] = []
    if elegidas and resto > 0:
        plan += [ItemPlan(elegidas[k % len(elegidas)][0], elegidas[k % len(elegidas)][1]) for k in range(resto)]
    elif resto > 0 and prioritarias:
        cupo_prioridad += resto
    elif resto > 0:
        # 5. Nada pendiente: las dominadas que hace más tiempo que no se practican
        antiguas = sorted(
            (c for c in generales if c.estado == DOMINIO_DOMINADO),
            key=lambda c: (c.ultima_practica or datetime.min, c.orden),
        )[:p.max_lecciones_resto]
        if antiguas:
            plan += _por_turnos([c.leccion_id for c in antiguas], resto, ZONA_NORMAL)
        else:
            # Solo quedan lecciones nuevas que no entraron (nuevas_por_sesion = 0): la primera
            plan += _por_turnos([por_orden[0].leccion_id], resto, ZONA_NORMAL)

    plan += _por_turnos(prioritarias, cupo_prioridad, ZONA_PRIORIDAD)
    plan += _por_turnos(list(refuerzo)[:n_refuerzo], n_refuerzo, ZONA_REFUERZO)
    plan += _por_turnos(list(extension)[:n_extension], n_extension, ZONA_EXTENSION)

    rng.shuffle(plan)
    especiales = (ZONA_EXTENSION, ZONA_REFUERZO)
    if plan[0].zona in especiales:
        k = next((i for i, it in enumerate(plan) if it.zona not in especiales), None)
        if k is not None:
            plan[0], plan[k] = plan[k], plan[0]
    return plan
