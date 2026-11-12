"""
Reglas de error del núcleo, separadas por camino.

A diferencia del enum único `TipoError` del sistema de decimales, cada camino define sus propias
reglas en su módulo (por ejemplo app/nucleo/lecciones/naturales/reglas.py), y el código de cada
regla lleva el camino delante: "naturales.suma.conto_uno_menos". Así añadir un camino no toca
los demás, y el registro de errores en la base es texto, sin migraciones por cada regla nueva.

Una regla es una función que, dado el problema y un hueco, devuelve las respuestas que daría un
estudiante que comete ese error. La misma regla sirve para dos cosas:
- generar las opciones incorrectas del banco;
- clasificar una respuesta incorrecta (la primera regla que la produce gana, así que el orden de
  la lista importa: van primero las más específicas).
"""

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from app.nucleo.problema import ProblemaExpresion

NO_CLASIFICADO = "no_clasificado"


@dataclass(frozen=True)
class ReglaError:
    codigo: str          # "<conjunto>.<habilidad>.<error>"
    descripcion: str     # para el profesor y para los informes
    candidatos: Callable[[ProblemaExpresion, str], Sequence[Any]]

    def __post_init__(self):
        partes = self.codigo.split(".")
        if len(partes) != 3 or not all(partes):
            raise ValueError(f"Código de regla inválido (se espera camino.error): {self.codigo}")

    @property
    def camino(self) -> str:
        return self.codigo.rsplit(".", 1)[0]

    def respuestas(self, problema: ProblemaExpresion, hueco_id: str) -> list:
        return list(self.candidatos(problema, hueco_id))


def clasificar(
    reglas: Sequence[ReglaError], problema: ProblemaExpresion, hueco_id: str, valor: Any
) -> str:
    """Código de la primera regla que produce `valor` en ese hueco, o NO_CLASIFICADO."""
    for regla in reglas:
        if valor in regla.respuestas(problema, hueco_id):
            return regla.codigo
    return NO_CLASIFICADO


def distractores(
    reglas: Sequence[ReglaError], problema: ProblemaExpresion, hueco_id: str
) -> list[tuple[str, Any]]:
    """(código, respuesta) de todas las reglas, en su orden. Puede haber repetidos."""
    return [(r.codigo, v) for r in reglas for v in r.respuestas(problema, hueco_id)]
