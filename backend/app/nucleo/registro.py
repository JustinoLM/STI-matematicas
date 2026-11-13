"""
Generadores disponibles, por id de lección del catálogo (curriculo_leccion.id).

Una lección habilitada sin generador aquí no se practica en el núcleo: el reparto de la sesión
la omite. Las pruebas comprueban que cada id existe en programa_meduca.yaml, que la lección
está incluida y que los caminos del generador son los de la lección.
"""

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.lecciones.naturales.g1_u02_l01 import NumerosHasta10
from app.nucleo.lecciones.naturales.g1_u02_l02 import FormarHasta10
from app.nucleo.lecciones.naturales.g1_u03_l01 import SumemosHorizontal
from app.nucleo.lecciones.naturales.g1_u03_l02 import RestemosHorizontal
from app.nucleo.lecciones.naturales.g1_u03_l03 import SumemosRestemos3Numeros
from app.nucleo.lecciones.naturales.g1_u04_l01 import NumerosHasta20
from app.nucleo.lecciones.naturales.g1_u04_l02 import OrdenarYUbicarHasta20
from app.nucleo.lecciones.naturales.g1_u04_l03 import ContarDe2YDe5
from app.nucleo.lecciones.naturales.g1_u05_l01 import Sumemos10
from app.nucleo.lecciones.naturales.g1_u05_l02 import SumemosCompletando10
from app.nucleo.lecciones.naturales.g1_u05_l03 import RestemosHasta19
from app.nucleo.lecciones.naturales.g1_u05_l04 import SumemosRestemos3NumerosHasta20
from app.nucleo.lecciones.naturales.g1_u05_l05 import SemirrectaHasta20
from app.nucleo.lecciones.naturales.g1_u06_l01 import ContarDe10En10
from app.nucleo.lecciones.naturales.g1_u06_l02 import NumerosHasta99
from app.nucleo.lecciones.naturales.g1_u06_l03 import DecenasYUnidades
from app.nucleo.lecciones.naturales.g1_u06_l04 import UbicarHasta99
from app.nucleo.lecciones.naturales.g1_u06_l05 import CompararHasta99
from app.nucleo.lecciones.naturales.g1_u07_l01 import SumemosHasta99
from app.nucleo.lecciones.naturales.g1_u07_l02 import RestemosHasta99
from app.nucleo.lecciones.naturales.g1_u07_l03 import SemirrectaHasta99

GENERADORES: dict[str, GeneradorLeccion] = {
    g.leccion_id: g
    for g in (
        # 1.º grado: numeración (U2, U4, U6; fase 5b)
        NumerosHasta10(),
        FormarHasta10(),
        NumerosHasta20(),
        OrdenarYUbicarHasta20(),
        ContarDe2YDe5(),
        ContarDe10En10(),
        NumerosHasta99(),
        DecenasYUnidades(),
        UbicarHasta99(),
        CompararHasta99(),
        # 1.º grado: suma y resta (U3, U5, U7; fase 5a)
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
