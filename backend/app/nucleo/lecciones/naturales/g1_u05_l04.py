"""
g1-u05-l04 "Sumemos y restemos 3 números hasta 20" (1.º grado, unidad 5).

Igual que U3 L3, con números y resultados parciales hasta 20 (18 − 5 − 6, 16 − 10 + 5, 9 + 7 − 7).
Al menos un número o un resultado parcial pasa de 10, para que no repita la lección de la U3.
"""

from app.nucleo.lecciones.naturales.comun import parciales
from app.nucleo.lecciones.naturales.reglas import R_DECENA, REGLAS_TRES_NUMEROS, S_DECENA
from app.nucleo.lecciones.naturales.tres_numeros import TresNumeros


class SumemosRestemos3NumerosHasta20(TresNumeros):
    leccion_id = "g1-u05-l04"
    version = 1
    MAXIMO = 20
    PRIMERO_MAX = 20
    OTROS_MAX = 10
    REGLAS = REGLAS_TRES_NUMEROS + (S_DECENA, R_DECENA)

    def _dentro(self, nums, ops) -> bool:
        todos = [*nums, *parciales(nums, ops)]
        return super()._dentro(nums, ops) and max(todos) > 10
