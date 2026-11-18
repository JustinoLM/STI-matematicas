"""
Estudiante de prueba para la motivación del núcleo (fase 7b): PRUEBA7B01 en el salón 1A (2026),
contraseña "prueba123". No toca a los demás estudiantes de 1A ni sus lecciones.

Su historia (práctica simulada del 6 de octubre al 13 de noviembre de 2026):
- Dominadas: U2 L1, U2 L2, U3 L1, U3 L2 y U4 L2 → medallas de esas lecciones, de la unidad 2 y el
  bronce de Numeración (3 de 10).
- U4 L1 "por confirmar" (dominio provisional, como si lo hubiera dado el diagnóstico).
- U3 L3 en práctica con 7 estrellas en sus últimos 9 problemas: el siguiente acierto la domina.
- Un diagnóstico terminado (para que no se le pida al entrar).
- Experiencia justo por debajo del nivel 5: al dominar U3 L3 en su próxima práctica sube de nivel y
  gana las medallas de la unidad 3 y el bronce de Suma y de Resta (sirve para ver las celebraciones).

Uso:
    cd backend
    poetry run python scripts/estudiante_prueba_7b.py --crear
    poetry run python scripts/estudiante_prueba_7b.py --borrar
"""

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from salon_demo_seguimiento import borrar_dependencias  # noqa: E402
from sqlalchemy import and_, select, text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.core.tiempo import inicio_dia_local_utc  # noqa: E402
from app.models.nucleo import (  # noqa: E402
    DIAGNOSTICO_AUTOMATICO,
    DIAGNOSTICO_TERMINADO,
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    PROBLEMA_TERMINADO,
    SESION_COMPLETADA,
    XP_ACIERTO,
    XP_LECCION_DOMINADA,
    XP_PRACTICA,
    ZONA_NORMAL,
    NucleoDiagnostico,
    NucleoDominio,
    NucleoExperiencia,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.models.school import (  # noqa: E402
    ANIO_ACTIVO,
    MATRICULA_ACTIVA,
    AnioLectivo,
    Matricula,
    Salon,
)
from app.models.user import Estudiante, Profesor  # noqa: E402
from app.nucleo.motivacion import experiencia_para_nivel  # noqa: E402
from app.nucleo.parametros import ParametrosNucleo  # noqa: E402

PREFIJO = "PRUEBA7B"
CODIGO = "PRUEBA7B01"
CONTRASENA = "prueba123"
SALON = "1A"

# (lección, [(día, aciertos de la sesión como texto "1101…")], estado final)
HISTORIA = [
    ("g1-u02-l01", [(date(2026, 11, 2), "11111"), (date(2026, 11, 3), "11011")], DOMINIO_DOMINADO),
    ("g1-u02-l02", [(date(2026, 11, 3), "11110"), (date(2026, 11, 4), "11111")], DOMINIO_DOMINADO),
    ("g1-u03-l01", [(date(2026, 11, 5), "11111"), (date(2026, 11, 6), "10111")], DOMINIO_DOMINADO),
    ("g1-u03-l02", [(date(2026, 11, 6), "11011"), (date(2026, 11, 9), "11101")], DOMINIO_DOMINADO),
    ("g1-u04-l02", [(date(2026, 11, 9), "11111"), (date(2026, 11, 10), "11011")], DOMINIO_DOMINADO),
    ("g1-u03-l03", [(date(2026, 11, 12), "10110"), (date(2026, 11, 13), "1111")], DOMINIO_EN_PROGRESO),
]
PROVISIONAL = "g1-u04-l01"
FALTA_PARA_SUBIR = 25          # experiencia que le falta para el nivel 5


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
        est = Estudiante(codigo_estudiante=CODIGO, password_hash=get_password_hash(CONTRASENA),
                         tipo_usuario="estudiante", nombre_completo="Prueba Motivación", organizacion_id=prof.organizacion_id)
        db.add(est)
        await db.flush()
        db.add(Matricula(anio_lectivo_id=anio.id, estudiante_id=est.id, estado=MATRICULA_ACTIVA,
                         fecha_ingreso=datetime(2026, 10, 1, 13)))
        db.add(NucleoDiagnostico(estudiante_id=est.id, anio_lectivo_id=anio.id, estado=DIAGNOSTICO_TERMINADO,
                                 origen=DIAGNOSTICO_AUTOMATICO, resultado=[], motivo_fin="completo", problemas=0,
                                 fecha_creacion=datetime(2026, 10, 1, 14), fecha_inicio=datetime(2026, 10, 1, 14),
                                 fecha_fin=datetime(2026, 10, 1, 14, 5)))
        xp = 0

        async def sesion(dia: date, lecciones: list[tuple[str, bool]]) -> list[NucleoProblemaSesion]:
            nonlocal xp
            inicio = inicio_dia_local_utc(dia) + timedelta(hours=14)      # 9:00 a. m. en Panamá
            s = NucleoSesion(estudiante_id=est.id, anio_lectivo_id=anio.id, estado=SESION_COMPLETADA, plan=[],
                             cantidad_problemas=len(lecciones), progreso=len(lecciones),
                             fecha_inicio=inicio, fecha_fin=inicio + timedelta(minutes=len(lecciones)))
            db.add(s)
            await db.flush()
            filas = []
            for i, (lec, acierto) in enumerate(lecciones):
                fin = inicio + timedelta(minutes=i + 1)
                ps = NucleoProblemaSesion(sesion_id=s.id, estudiante_id=est.id, orden=i, leccion_id=lec, zona=ZONA_NORMAL,
                                          problema={}, estado=PROBLEMA_TERMINADO, intentos=1 if acierto else 3,
                                          correcto=acierto, acierto=acierto, fecha_creacion=fin, fecha_fin=fin)
                db.add(ps)
                await db.flush()
                db.add(NucleoExperiencia(estudiante_id=est.id, tipo=XP_PRACTICA, cantidad=1, leccion_id=lec,
                                         problema_sesion_id=ps.id, fecha=fin))
                xp += 1
                if acierto:
                    db.add(NucleoExperiencia(estudiante_id=est.id, tipo=XP_ACIERTO, cantidad=2, leccion_id=lec,
                                             problema_sesion_id=ps.id, fecha=fin))
                    xp += 2
                filas.append(ps)
            return filas

        # Práctica de octubre (repaso de numeración) para llegar cerca del nivel 5
        p = ParametrosNucleo()
        bonos = sum(50 for _, _, e in HISTORIA if e == DOMINIO_DOMINADO)
        historia_xp = sum(len(a) + 2 * a.count("1") for _, dias, _ in HISTORIA for _, a in dias)
        relleno = experiencia_para_nivel(5, p) - FALTA_PARA_SUBIR - bonos - historia_xp
        dia = date(2026, 10, 6)
        while relleno > 0:
            n = min(10, (relleno + 2) // 3)
            await sesion(dia, [("g1-u02-l01", True)] * n)
            relleno -= 3 * n
            dia += timedelta(days=2)

        for lec, dias, estado in HISTORIA:
            ultimo = None
            for d, aciertos in dias:
                ultimo = (await sesion(d, [(lec, c == "1") for c in aciertos]))[-1]
            dom = NucleoDominio(estudiante_id=est.id, leccion_id=lec, estado=estado, fecha_inicio=ultimo.fecha_fin,
                                ultima_practica=ultimo.fecha_fin)
            if estado == DOMINIO_DOMINADO:
                dom.fecha_dominio = ultimo.fecha_fin
                db.add(NucleoExperiencia(estudiante_id=est.id, tipo=XP_LECCION_DOMINADA, cantidad=50, leccion_id=lec,
                                         problema_sesion_id=ultimo.id, primera_vez=True, fecha=ultimo.fecha_fin))
                xp += 50
            db.add(dom)
        db.add(NucleoDominio(estudiante_id=est.id, leccion_id=PROVISIONAL, estado=DOMINIO_PROVISIONAL,
                             fecha_inicio=datetime(2026, 10, 1, 14, 5)))
        await db.commit()
        print(f"Creado {CODIGO} (contraseña {CONTRASENA}) en {SALON} (año lectivo {anio.id}) con {xp} de experiencia "
              f"(el nivel 5 empieza en {experiencia_para_nivel(5, p)}).")
        return 0


async def borrar() -> int:
    async with AsyncSessionLocal() as db:
        ests = list((await db.execute(
            select(Estudiante.id).where(Estudiante.codigo_estudiante.op("~")(f"^{PREFIJO}[0-9]{{2}}$"))
        )).scalars())
        if not ests:
            print("No hay nada que borrar.")
            return 0
        p = {"e": ests, "a": [0]}           # solo sus filas: el año lectivo de 1A no se toca
        if not await borrar_dependencias(db, p):
            await db.rollback()
            return 1
        await db.execute(text("DELETE FROM estudiante WHERE id = ANY(:e)"), p)
        await db.execute(text("DELETE FROM usuario WHERE id = ANY(:e)"), p)
        await db.commit()
        print(f"Borrados {len(ests)} estudiantes {PREFIJO}*.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Estudiante de prueba de la motivación del núcleo (fase 7b).")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--crear", action="store_true")
    grupo.add_argument("--borrar", action="store_true")
    args = parser.parse_args()
    return asyncio.run(crear() if args.crear else borrar())


if __name__ == "__main__":
    sys.exit(main())
