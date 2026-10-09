"""
Audita la caché de enunciados temáticos (tabla enunciado_tematico).

Elimina:
  - enunciados cuyo texto no contiene exactamente los números del problema,
  - enunciados de temas que ya no existen (clave distinta a las de LLMPrompts).

Uso:
    poetry run python scripts/auditar_enunciados.py          # solo informa
    poetry run python scripts/auditar_enunciados.py --borrar # elimina los inválidos
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.llm import EnunciadoTematico  # noqa: E402
from app.models.problem import Problema  # noqa: E402
from app.services.enunciados_service import EnunciadosService  # noqa: E402
from app.services.llm_service import LLMPrompts  # noqa: E402


async def main(borrar: bool) -> None:
    async with AsyncSessionLocal() as db:
        filas = (
            await db.execute(
                select(EnunciadoTematico, Problema.numero1, Problema.numero2).join(
                    Problema, Problema.signature == EnunciadoTematico.signature, isouter=True
                )
            )
        ).all()

        invalidos = []
        for e, n1, n2 in filas:
            tema_ok = e.tema in LLMPrompts._TEMAS_CONFIG
            numeros_ok = (
                n1 is not None and EnunciadosService.contiene_numeros_exactos(e.texto, n1, n2)
            )
            if not (tema_ok and numeros_ok):
                invalidos.append(e)

        print(f"Enunciados en caché: {len(filas)}")
        print(f"Inválidos (tema desconocido o números distintos): {len(invalidos)}")
        if borrar and invalidos:
            for e in invalidos:
                await db.execute(
                    delete(EnunciadoTematico).where(
                        EnunciadoTematico.signature == e.signature,
                        EnunciadoTematico.tema == e.tema,
                        EnunciadoTematico.nivel == e.nivel,
                        EnunciadoTematico.variacion == e.variacion,
                    )
                )
            await db.commit()
            print(f"Eliminados: {len(invalidos)}")


if __name__ == "__main__":
    asyncio.run(main("--borrar" in sys.argv))
