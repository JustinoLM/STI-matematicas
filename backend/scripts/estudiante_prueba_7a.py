"""
Estudiantes de prueba para el diagnóstico inicial (fase 7a): PRUEBA7A01 y PRUEBA7A02 en el salón
1A (2026), sin práctica previa, así el diagnóstico les toca al entrar a practicar.

Contraseña: "prueba123". No toca a los demás estudiantes de 1A ni sus lecciones.

Uso:
    cd backend
    poetry run python scripts/estudiante_prueba_7a.py --crear
    poetry run python scripts/estudiante_prueba_7a.py --borrar
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from salon_demo_seguimiento import borrar_dependencias  # noqa: E402
from sqlalchemy import and_, select, text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.school import (  # noqa: E402
    ANIO_ACTIVO,
    MATRICULA_ACTIVA,
    AnioLectivo,
    Matricula,
    Salon,
)
from app.models.user import Estudiante, Profesor  # noqa: E402

PREFIJO = "PRUEBA7A"
CONTRASENA = "prueba123"
NOMBRES = ["Prueba Diagnóstico Uno", "Prueba Diagnóstico Dos"]
SALON = "1A"


async def crear() -> int:
    async with AsyncSessionLocal() as db:
        prof = (await db.execute(select(Profesor).where(Profesor.codigo_profesor == "PROF001"))).scalar_one_or_none()
        if prof is None or prof.organizacion_id is None:
            print("No existe PROF001 con organización.", file=sys.stderr)
            return 1
        anio = (await db.execute(
            select(AnioLectivo).join(Salon, Salon.id == AnioLectivo.salon_id)
            .where(and_(Salon.organizacion_id == prof.organizacion_id, Salon.nombre == SALON,
                        AnioLectivo.estado == ANIO_ACTIVO))
        )).scalar_one_or_none()
        if anio is None:
            print(f"No hay un año activo del salón {SALON}.", file=sys.stderr)
            return 1
        if (await db.execute(select(Estudiante).where(Estudiante.codigo_estudiante.like(f"{PREFIJO}%")))).first():
            print(f"Ya hay estudiantes {PREFIJO}*: bórralos antes con --borrar.", file=sys.stderr)
            return 1
        hash_ = get_password_hash(CONTRASENA)
        for i, nombre in enumerate(NOMBRES, start=1):
            e = Estudiante(codigo_estudiante=f"{PREFIJO}{i:02d}", password_hash=hash_, tipo_usuario="estudiante",
                           nombre_completo=nombre, organizacion_id=prof.organizacion_id)
            db.add(e)
            await db.flush()
            db.add(Matricula(anio_lectivo_id=anio.id, estudiante_id=e.id, estado=MATRICULA_ACTIVA,
                             fecha_ingreso=datetime.utcnow()))
        await db.commit()
        print(f"Creados {PREFIJO}01 y {PREFIJO}02 (contraseña {CONTRASENA}) en {SALON} (año lectivo {anio.id}).")
        return 0


async def borrar() -> int:
    async with AsyncSessionLocal() as db:
        ests = list((await db.execute(
            select(Estudiante.id).where(Estudiante.codigo_estudiante.op("~")(f"^{PREFIJO}[0-9]{{2}}$"))
        )).scalars())
        if not ests:
            print("No hay nada que borrar.")
            return 0
        # Solo sus filas: el año lectivo de 1A no se toca
        p = {"e": ests, "a": [0]}
        if not await borrar_dependencias(db, p):
            await db.rollback()
            return 1
        await db.execute(text("DELETE FROM estudiante WHERE id = ANY(:e)"), p)
        await db.execute(text("DELETE FROM usuario WHERE id = ANY(:e)"), p)
        await db.commit()
        print(f"Borrados {len(ests)} estudiantes {PREFIJO}*.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Estudiantes de prueba del diagnóstico inicial (fase 7a).")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--crear", action="store_true")
    grupo.add_argument("--borrar", action="store_true")
    args = parser.parse_args()
    return asyncio.run(crear() if args.crear else borrar())


if __name__ == "__main__":
    sys.exit(main())
