"""
Motivación del núcleo (fase 7b). Lógica pura: nivel de jugador, bono por dominar, medallas y avance
hacia el dominio. Todo se calcula a partir de lo ya guardado (nucleo_experiencia y nucleo_dominio);
solo las medallas ganadas se guardan, para que no se pierdan si una lección vuelve a "en progreso".

**Nivel de jugador.** Es una recompensa, no decide la práctica. Sale de la experiencia acumulada
(suma de nucleo_experiencia), que nunca baja; por eso el nivel nunca baja.
- Para pasar del nivel n al n+1 hacen falta `nivel_base + nivel_incremento·(n−1)` de experiencia
  (con 60 y 60: 60, 120, 180…, es decir 60·n). Acumulado para llegar al nivel L: base·(L−1) + inc·(L−1)(L−2)/2.

**Bono por dominar (pregunta abierta 15).**
- Completo (`xp_bono_dominio`) la primera vez que domina la lección. Confirmar un dominio provisional
  del diagnóstico cuenta como primera vez; el provisional en sí no da bono.
- Si la vuelve a dominar tras un repaso fallido: `xp_bono_recuperada` del bono ("¡La recuperaste!").

**Medallas.** Se ganan una sola vez. Las lecciones que cuentan son las que alguna vez dominó (evento
"lección dominada"), aunque después hayan vuelto a "en progreso".
- Por lección dominada.
- Por unidad completa: todas las lecciones de la unidad (con generador) dominadas.
- Por hito del camino, dentro del grado: bronce, plata y oro al dominar `medalla_hito_*` de sus
  lecciones (25 / 50 / 100 %).

**Tienda (pregunta abierta 14).** Para quien practica en el núcleo, el requisito de nivel de un
artículo (escala vieja de 1 a 5) se compara con el nivel de jugador reescalado: 1 + factor·(r−1).
"""

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from app.nucleo.parametros import ParametrosNucleo

MEDALLA_LECCION = "leccion"
MEDALLA_UNIDAD = "unidad"
MEDALLA_CAMINO = "camino"
TIPOS_MEDALLA = (MEDALLA_LECCION, MEDALLA_UNIDAD, MEDALLA_CAMINO)
BRONCE, PLATA, ORO = "bronce", "plata", "oro"
SIN_GRADO = ""          # medallas de lección y de unidad: un solo grado de medalla


# ─── Nivel ───────────────────────────────────────────────────────────────────

def costo_nivel(n: int, p: ParametrosNucleo) -> int:
    """Experiencia para pasar del nivel n al n+1."""
    return p.nivel_base + p.nivel_incremento * (n - 1)


def experiencia_para_nivel(nivel: int, p: ParametrosNucleo) -> int:
    """Experiencia acumulada con la que se llega a `nivel` (el nivel 1 empieza en 0)."""
    k = nivel - 1
    return p.nivel_base * k + p.nivel_incremento * k * (k - 1) // 2


@dataclass(frozen=True)
class Nivel:
    nivel: int
    experiencia: int            # total acumulado
    en_el_nivel: int            # experiencia desde que empezó este nivel
    para_subir: int             # lo que cuesta este nivel completo

    @property
    def fraccion(self) -> float:
        return self.en_el_nivel / self.para_subir if self.para_subir else 1.0


def nivel_de(experiencia: int, p: ParametrosNucleo) -> Nivel:
    experiencia = max(int(experiencia), 0)
    # Estimación cerrada y ajuste (evita recorrer niveles uno a uno)
    nivel = 1
    if p.nivel_incremento > 0:
        a, b = p.nivel_incremento / 2, p.nivel_base - p.nivel_incremento / 2
        k = (-b + math.sqrt(b * b + 4 * a * experiencia)) / (2 * a)
        nivel = max(int(k) + 1, 1)
    elif p.nivel_base > 0:
        nivel = experiencia // p.nivel_base + 1
    while nivel > 1 and experiencia_para_nivel(nivel, p) > experiencia:
        nivel -= 1
    while experiencia_para_nivel(nivel + 1, p) <= experiencia:
        nivel += 1
    inicio = experiencia_para_nivel(nivel, p)
    return Nivel(nivel, experiencia, experiencia - inicio, costo_nivel(nivel, p))


def bono_dominio(primera_vez: bool, p: ParametrosNucleo) -> int:
    return p.xp_bono_dominio if primera_vez else round(p.xp_bono_dominio * p.xp_bono_recuperada)


def nivel_tienda(requisito: int, p: ParametrosNucleo) -> int:
    """Requisito de un artículo (escala vieja de 1 a 5) en la escala del nivel de jugador."""
    return 1 + p.nivel_tienda_factor * (max(int(requisito or 1), 1) - 1)


# ─── Medallas ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LeccionMapa:
    id: str
    grado: int
    unidad_numero: int
    unidad_titulo: str
    leccion_numero: int
    titulo: str
    orden: int
    caminos: tuple[str, ...] = ()


@dataclass(frozen=True)
class Medalla:
    tipo: str
    clave: str              # lección, "g1-u03" o "naturales.suma@1"
    grado_medalla: str      # "" o bronce / plata / oro
    titulo: str
    descripcion: str
    meta: int               # lecciones que hay que dominar
    logradas: int           # lecciones dominadas que cuentan


def clave_unidad(lec: LeccionMapa) -> str:
    return f"g{lec.grado}-u{lec.unidad_numero:02d}"


def clave_camino(camino: str, grado: int) -> str:
    return f"{camino}@{grado}"


def hitos(p: ParametrosNucleo) -> list[tuple[str, float]]:
    return [(BRONCE, p.medalla_hito_bronce), (PLATA, p.medalla_hito_plata), (ORO, p.medalla_hito_oro)]


def catalogo_medallas(
    lecciones: Sequence[LeccionMapa],
    dominadas: Iterable[str],
    nombres_camino: Mapping[str, str],
    p: ParametrosNucleo,
) -> list[Medalla]:
    """Todas las medallas posibles con las lecciones dadas (las del grado, con generador), con
    cuántas lecciones lleva para cada una. Ganada = logradas >= meta."""
    dominadas = set(dominadas)
    ordenadas = sorted(lecciones, key=lambda x: (x.orden, x.id))
    medallas: list[Medalla] = []
    for lec in ordenadas:
        medallas.append(Medalla(MEDALLA_LECCION, lec.id, SIN_GRADO, lec.titulo,
                                f"Dominaste {lec.grado}.º U{lec.unidad_numero} L{lec.leccion_numero}.",
                                1, int(lec.id in dominadas)))
    unidades: dict[str, list[LeccionMapa]] = {}
    for lec in ordenadas:
        unidades.setdefault(clave_unidad(lec), []).append(lec)
    for clave, ls in unidades.items():
        medallas.append(Medalla(MEDALLA_UNIDAD, clave, SIN_GRADO, ls[0].unidad_titulo,
                                f"Completaste la unidad {ls[0].unidad_numero} de {ls[0].grado}.º.",
                                len(ls), sum(x.id in dominadas for x in ls)))
    caminos: dict[str, list[LeccionMapa]] = {}
    for lec in ordenadas:
        for cam in lec.caminos:
            caminos.setdefault(clave_camino(cam, lec.grado), []).append(lec)
    for clave, ls in caminos.items():
        cam, grado = clave.split("@")
        logradas = sum(x.id in dominadas for x in ls)
        for nombre, fraccion in hitos(p):
            meta = max(1, math.ceil(len(ls) * fraccion - 1e-9))
            medallas.append(Medalla(MEDALLA_CAMINO, clave, nombre, nombres_camino.get(cam, cam),
                                    f"Dominaste {meta} de las {len(ls)} lecciones de este camino en {grado}.º.",
                                    meta, logradas))
    return medallas


def ganadas(medallas: Iterable[Medalla]) -> list[Medalla]:
    return [m for m in medallas if m.logradas >= m.meta]


# ─── Avance hacia el dominio de una lección ──────────────────────────────────

def casillas_dominio(aciertos: Sequence[bool], p: ParametrosNucleo) -> dict:
    """Los últimos `ventana_dominio` problemas como casillas (True acierto, False no, None vacía)
    y la meta: no se muestra nada que "reste"; una casilla sin acierto se ve vacía."""
    ultimos = list(aciertos[-p.ventana_dominio:])
    casillas: list[Optional[bool]] = ultimos + [None] * (p.ventana_dominio - len(ultimos))
    return {
        "casillas": casillas,
        "aciertos": sum(1 for a in ultimos if a),
        "meta": math.ceil(p.ventana_dominio * p.umbral_dominio - 1e-9),
        "ventana": p.ventana_dominio,
    }
