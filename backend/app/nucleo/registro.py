"""
Generadores disponibles, por id de lección del catálogo (curriculo_leccion.id).

Una lección habilitada sin generador aquí no se practica en el núcleo: el reparto de la sesión
la omite. Las pruebas comprueban que cada id existe en programa_meduca.yaml, que la lección
está incluida y que los caminos del generador son los de la lección.
"""

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.lecciones.naturales.g1_u03_l01 import SumemosHorizontal
from app.nucleo.lecciones.naturales.g1_u03_l02 import RestemosHorizontal
from app.nucleo.lecciones.naturales.g1_u03_l03 import SumemosRestemos3Numeros
from app.nucleo.lecciones.naturales.g1_u05_l01 import Sumemos10
from app.nucleo.lecciones.naturales.g1_u05_l02 import SumemosCompletando10
from app.nucleo.lecciones.naturales.g1_u05_l03 import RestemosHasta19
from app.nucleo.lecciones.naturales.g1_u05_l04 import SumemosRestemos3NumerosHasta20
from app.nucleo.lecciones.naturales.g1_u05_l05 import SemirrectaHasta20
from app.nucleo.lecciones.naturales.g1_u07_l01 import SumemosHasta99
from app.nucleo.lecciones.naturales.g1_u07_l02 import RestemosHasta99
from app.nucleo.lecciones.naturales.g1_u07_l03 import SemirrectaHasta99

GENERADORES: dict[str, GeneradorLeccion] = {
    g.leccion_id: g
    for g in (
        # 1.º grado: suma y resta (U3, U5, U7)
        SumemosHorizontal(),
        RestemosHorizontal(),
        SumemosRestemos3Numeros(),
        Sumemos10(),
        SumemosCompletando10(),
        RestemosHasta19(),
        SumemosRestemos3NumerosHasta20(),
        SemirrectaHasta20(),
        SumemosHasta99(),
        RestemosHasta99(),
        SemirrectaHasta99(),
    )
}


def obtener_generador(leccion_id: str) -> GeneradorLeccion:
    try:
        return GENERADORES[leccion_id]
    except KeyError:
        raise KeyError(f"La lección {leccion_id} no tiene generador en el núcleo") from None


def tiene_generador(leccion_id: str) -> bool:
    return leccion_id in GENERADORES
