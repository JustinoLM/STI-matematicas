"""
Carga el catálogo de lecciones y el grafo de prerrequisitos por defecto en la base.

Fuente: backend/curriculo/programa_meduca.yaml (ver docs/DISENO_MODULAR.md, sección 1).
Valida todo antes de escribir; si hay errores, los lista y no toca la base. Es idempotente:
volver a correrlo sin cambios en el archivo no modifica nada.

Uso:
    cd backend
    poetry run python scripts/cargar_curriculo.py                 # valida y carga
    poetry run python scripts/cargar_curriculo.py --solo-validar  # solo valida el archivo
    poetry run python scripts/cargar_curriculo.py --archivo otro.yaml
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.services.curriculo_service import (  # noqa: E402
    RUTA_PROGRAMA,
    ErrorCurriculo,
    cargar_programa,
    leer_programa,
    validar_programa,
)


def _imprimir_errores(errores: list[str]) -> None:
    print(f"El currículo tiene {len(errores)} error(es); no se cargó nada:", file=sys.stderr)
    for e in errores:
        print(f"  - {e}", file=sys.stderr)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Carga el currículo (catálogo y prerrequisitos).")
    parser.add_argument("--archivo", type=Path, default=RUTA_PROGRAMA)
    parser.add_argument("--solo-validar", action="store_true")
    args = parser.parse_args()

    try:
        programa = leer_programa(args.archivo)
    except ErrorCurriculo as e:
        _imprimir_errores(e.errores)
        return 1

    errores = validar_programa(programa)
    if errores:
        _imprimir_errores(errores)
        return 1

    incluidas = sum(1 for lec in programa.lecciones if lec.incluida)
    print(f"Archivo válido: {len(programa.lecciones)} lecciones ({incluidas} incluidas), "
          f"{len(programa.caminos)} caminos.")
    if args.solo_validar:
        return 0

    async with AsyncSessionLocal() as db:
        try:
            resumen = await cargar_programa(db, programa)
        except ErrorCurriculo as e:
            await db.rollback()
            _imprimir_errores(e.errores)
            return 1
        await db.commit()

    if not resumen.hubo_cambios:
        print("Sin cambios: la base ya coincide con el archivo.")
        return 0
    print(
        "Carga terminada.\n"
        f"  Caminos: {resumen.caminos_creados} creados, {resumen.caminos_actualizados} actualizados, "
        f"{resumen.caminos_eliminados} eliminados\n"
        f"  Lecciones: {resumen.lecciones_creadas} creadas, {resumen.lecciones_actualizadas} actualizadas\n"
        f"  Caminos de lecciones: +{resumen.enlaces_camino_agregados} / -{resumen.enlaces_camino_quitados}\n"
        f"  Prerrequisitos: +{resumen.prerrequisitos_agregados} / -{resumen.prerrequisitos_quitados}"
    )
    for linea in resumen.detalle:
        print(f"  · {linea}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
