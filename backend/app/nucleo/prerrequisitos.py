"""
Grafo de prerrequisitos de un año lectivo (fase 6a).

El currículo trae los prerrequisitos por defecto (curriculo_prerrequisito). El profesor puede
editar los de una lección en el año lectivo de su salón; esa lección queda marcada como editada y
usa los del año, aunque queden vacíos. Las demás siguen con los del currículo, así que recargar el
currículo actualiza lo que el profesor no tocó y nunca pisa lo que sí editó.

Todo es puro; la carga desde la base está en servicios/grafo.py.
"""

from typing import Iterable, Mapping, Optional


def combinar(
    defecto: Mapping[str, Iterable[str]],
    editadas: Iterable[str],
    del_anio: Mapping[str, Iterable[str]],
) -> dict[str, tuple[str, ...]]:
    """Prerrequisitos que se aplican: los del año en las lecciones editadas, los del currículo en
    las demás. Una lección sin prerrequisitos no aparece."""
    editadas = set(editadas)
    efectivo = {lec: tuple(pres) for lec, pres in defecto.items() if lec not in editadas}
    for lec in editadas:
        pres = tuple(del_anio.get(lec, ()))
        if pres:
            efectivo[lec] = pres
    return efectivo


def camino_de_ciclo(
    prerrequisitos: Mapping[str, Iterable[str]], leccion_id: str, nuevos: Iterable[str]
) -> Optional[list[str]]:
    """Si dar a `leccion_id` los prerrequisitos `nuevos` forma un ciclo, devuelve el camino
    [p, ..., leccion_id]: p (uno de los nuevos) ya depende, directa o indirectamente, de la
    lección. Si no hay ciclo, None. Ignora los prerrequisitos actuales de `leccion_id`."""
    for inicio in nuevos:
        if inicio == leccion_id:
            return [leccion_id]
        # Búsqueda en profundidad siguiendo "depende de" desde `inicio`
        pila: list[tuple[str, list[str]]] = [(inicio, [inicio])]
        vistos = {inicio}
        while pila:
            actual, camino = pila.pop()
            for pre in prerrequisitos.get(actual, ()):
                if pre == leccion_id:
                    return camino + [leccion_id]
                if pre not in vistos:
                    vistos.add(pre)
                    pila.append((pre, camino + [pre]))
    return None
