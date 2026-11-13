"""
Habilita lecciones del núcleo en un salón para probar la pantalla de práctica (fase 4).

Solo crea o actualiza la habilitación de las lecciones indicadas en el año lectivo activo del
salón, con el profesor de ese año. No toca estudiantes, sesiones ni dominio. Es idempotente.

Requisitos: la base al día (`poetry run alembic upgrade head`) y el currículo cargado
(`poetry run python scripts/cargar_curriculo.py`).

Uso:
    cd backend
    poetry run python scripts/habilitar_nucleo_prueba.py                     # g1-u03-l01 en 1A
    poetry run python scripts/habilitar_nucleo_prueba.py --signo azar        # también el signo oculto
    poetry run python scripts/habilitar_nucleo_prueba.py --salon 1A --leccion g1-u03-l01
    poetry run python scripts/habilitar_nucleo_prueba.py --deshabilitar      # la deshabilita
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import and_, select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.curriculo import LeccionCurricular  # noqa: E402
from app.models.school import AnioLectivo, Salon  # noqa: E402
from app.nucleo.modos import Modo  # noqa: E402
from app.nucleo.registro import tiene_generador  # noqa: E402
from app.nucleo.servicios.habilitacion import ServicioHabilitacion  # noqa: E402
from app.services.school_service import ErrorSalon  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Habilita lecciones del núcleo en un salón de prueba.")
    parser.add_argument("--salon", default="1A", help="Nombre del salón (por defecto 1A)")
    parser.add_argument("--leccion", action="append", help="Id de lección (repetible; por defecto g1-u03-l01)")
    parser.add_argument("--signo", choices=[m.value for m in Modo], default=Modo.SIEMPRE.value)
    parser.add_argument("--iconos", choices=[m.value for m in Modo], default=Modo.SIEMPRE.value)
    parser.add_argument("--deshabilitar", action="store_true")
    args = parser.parse_args()
    lecciones = args.leccion or ["g1-u03-l01"]

    async with AsyncSessionLocal() as db:
        if await db.scalar(select(LeccionCurricular.id).limit(1)) is None:
            print("El currículo no está cargado: corre scripts/cargar_curriculo.py.", file=sys.stderr)
            return 1
        anio = (await db.execute(
            select(AnioLectivo).join(Salon, Salon.id == AnioLectivo.salon_id)
            .where(and_(Salon.nombre == args.salon, AnioLectivo.estado == "activo"))
        )).scalar_one_or_none()
        if anio is None:
            print(f"No hay un año lectivo activo para el salón {args.salon}.", file=sys.stderr)
            return 1

        servicio = ServicioHabilitacion(db)
        try:
            for leccion_id in lecciones:
                if args.deshabilitar:
                    await servicio.deshabilitar(anio.id, anio.profesor_id, leccion_id)
                    print(f"{leccion_id}: deshabilitada en {args.salon} (año {anio.anio}).")
                    continue
                if not tiene_generador(leccion_id):
                    print(f"Aviso: {leccion_id} no tiene generador; el reparto la omitirá.")
                await servicio.habilitar(anio.id, anio.profesor_id, leccion_id,
                                         signo=Modo(args.signo), iconos=Modo(args.iconos))
                print(f"{leccion_id}: habilitada en {args.salon} (año {anio.anio}), "
                      f"signo={args.signo}, iconos={args.iconos}.")
        except ErrorSalon as e:
            print(f"Error: {e}", file=sys.stderr)
            await db.rollback()
            return 1
        await db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
