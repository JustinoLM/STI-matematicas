"""
Generadores disponibles, por id de lección del catálogo (curriculo_leccion.id).

Una lección habilitada sin generador aquí no se practica en el núcleo: el reparto de la sesión
la omite. Las pruebas comprueban que cada id existe en programa_meduca.yaml, que la lección
está incluida y que los caminos del generador son los de la lección.
"""

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.lecciones.naturales.g1_u03_l01 import SumemosHorizontal

GENERADORES: dict[str, GeneradorLeccion] = {
    g.leccion_id: g
    for g in (
        SumemosHorizontal(),
    )
}


def obtener_generador(leccion_id: str) -> GeneradorLeccion:
    try:
        return GENERADORES[leccion_id]
    except KeyError:
        raise KeyError(f"La lección {leccion_id} no tiene generador en el núcleo") from None


def tiene_generador(leccion_id: str) -> bool:
    return leccion_id in GENERADORES
