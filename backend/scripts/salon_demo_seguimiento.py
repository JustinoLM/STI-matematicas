"""
Salón de prueba para el seguimiento del profesor (fase 6b): "Demo seguimiento" (1.º), aparte de 1A.

Crea, en la organización de PROF001 y con PROF001 como profesor:
- 25 estudiantes ficticios DEMO01 a DEMO25 (contraseña "demo123");
- 8 lecciones de 1.º habilitadas (g1-u03-l02 prioritaria; g1-u03-l01 queda sin habilitar para que
  el refuerzo y la asignación desde una alerta tengan sentido);
- práctica simulada del 24 de agosto al 12 de noviembre de 2026 (sesiones, problemas, intentos con
  errores clasificados, dominio y lecciones dominadas), con perfiles variados:
  6 dominan casi todo, 9 en progreso, 4 atascados (2 con refuerzo que no basta, 1 sin refuerzo
  posible, 1 que va detrás del salón), 1 que sobresale en la extensión, 2 en repaso y 3 sin empezar;
- un salón cerrado de 2025 ("Demo K") con dos de ellos, para el historial de la ficha.

Es reproducible (semilla fija) y se borra entero con --borrar (por los códigos DEMO y los salones
"Demo seguimiento" y "Demo K"; no toca 1A ni ningún otro salón).

Uso:
    cd backend
    poetry run python scripts/salon_demo_seguimiento.py --crear
    poetry run python scripts/salon_demo_seguimiento.py --borrar
"""

import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import and_, select, text  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.nucleo import (  # noqa: E402
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    PROBLEMA_TERMINADO,
    SESION_COMPLETADA,
    XP_LECCION_DOMINADA,
    ZONA_EXTENSION,
    ZONA_NORMAL,
    ZONA_PRIORIDAD,
    ZONA_REFUERZO,
    NucleoDominio,
    NucleoExperiencia,
    NucleoIntento,
    NucleoProblemaSesion,
    NucleoSesion,
)
from app.models.school import (  # noqa: E402
    ANIO_ACTIVO,
    ANIO_CERRADO,
    MATRICULA_ACTIVA,
    MATRICULA_CERRADA,
    AnioLectivo,
    Matricula,
    Salon,
)
from app.models.user import Estudiante, Profesor  # noqa: E402
from app.nucleo.registro import obtener_generador  # noqa: E402
from app.nucleo.servicios.habilitacion import ServicioHabilitacion  # noqa: E402
from app.services.school_service import SchoolService  # noqa: E402

SALON = "Demo seguimiento"
SALON_ANTERIOR = "Demo K"
PREFIJO = "DEMO"
CONTRASENA = "demo123"

HABILITADAS = ["g1-u02-l01", "g1-u02-l02", "g1-u03-l02", "g1-u03-l03", "g1-u04-l01", "g1-u04-l02",
               "g1-u05-l01", "g1-u06-l01"]
PRIORITARIA = "g1-u03-l02"
PRE_NO_HABILITADO = "g1-u03-l01"     # prerrequisito de g1-u03-l02, para el refuerzo
EXTENSION = "g1-u05-l03"             # sucesora de g1-u03-l02 y g1-u05-l01, sin habilitar

NOMBRES = [
    "Valentina Castillo", "Mateo Herrera", "Isabella Morales", "Santiago Vargas", "Camila Rojas",
    "Sebastián Ortega", "Lucía Navarro", "Diego Peña", "Mariana Cedeño", "Andrés Batista",
    "Sofía Quintero", "Gabriel Saavedra", "Emma Barrios", "Daniel Pineda", "Victoria Araúz",
    "Nicolás Jaén", "Martina Delgado", "Samuel Córdoba", "Antonella Vega", "Thiago Mendoza",
    "Renata Solís", "Joaquín Ábrego", "Paula Guerra", "Emiliano Ríos", "Julieta Montenegro",
]

INICIO = datetime(2026, 8, 24, 14, 0)     # T2 (termina el 4 de septiembre)
FIN = datetime(2026, 11, 12, 14, 0)       # T3
rng = random.Random(2026)


def dias_de_practica(n: int, desde: datetime = INICIO, hasta: datetime = FIN) -> list[datetime]:
    """n días entre desde y hasta; el último es siempre `hasta` (la práctica más reciente)."""
    total = (hasta - desde).days
    dias = sorted(rng.sample(range(total), min(n - 1, total))) + [total]
    return [desde + timedelta(days=d, minutes=rng.randint(0, 120)) for d in dias]


def serie(n: int, precision: float, final_bueno: bool = False) -> list[bool]:
    """n resultados con la precisión dada; con final_bueno, los últimos 10 llegan al dominio."""
    if precision < 0.6:
        # Atascados: aciertos repartidos parejo, para que cualquier ventana quede por debajo
        return [int((i + 1) * precision) > int(i * precision) for i in range(n)]
    r = [rng.random() < precision for _ in range(n)]
    if final_bueno:
        r[-10:] = [True] * 4 + [False] + [True] * 5
    return r


class Simulador:
    def __init__(self, db, anio_id: int):
        self.db = db
        self.anio_id = anio_id

    async def practica(self, est_id: int, items: list[tuple[str, str, bool]], fechas: list[datetime]) -> dict[str, NucleoProblemaSesion]:
        """Reparte los problemas (lección, zona, acierto) en sesiones de hasta 10, una por fecha.
        Devuelve el último problema de cada lección (para fechar el dominio)."""
        ultimos: dict[str, NucleoProblemaSesion] = {}
        por_sesion = max(1, -(-len(items) // max(len(fechas), 1)))
        for i, fecha in enumerate(fechas):
            lote = items[i * por_sesion:(i + 1) * por_sesion]
            if not lote:
                break
            s = NucleoSesion(estudiante_id=est_id, anio_lectivo_id=self.anio_id, estado=SESION_COMPLETADA,
                             plan=[{"leccion_id": lec, "zona": zona} for lec, zona, _ in lote],
                             cantidad_problemas=len(lote), progreso=len(lote), fecha_inicio=fecha,
                             fecha_fin=fecha + timedelta(minutes=len(lote)))
            self.db.add(s)
            await self.db.flush()
            for orden, (lec, zona, acierto) in enumerate(lote):
                momento = fecha + timedelta(seconds=40 * orden)
                ps = NucleoProblemaSesion(
                    sesion_id=s.id, estudiante_id=est_id, orden=orden, leccion_id=lec, zona=zona,
                    problema={"leccion_id": lec, "demo": True}, estado=PROBLEMA_TERMINADO,
                    intentos=1 if acierto else 2, correcto=True, acierto=acierto,
                    fecha_creacion=momento, fecha_fin=momento + timedelta(seconds=30))
                self.db.add(ps)
                await self.db.flush()
                if not acierto:
                    reglas = list(obtener_generador(lec).reglas_error())
                    # Pocos errores frecuentes por estudiante: pesa más las primeras reglas
                    regla = reglas[min(int(rng.expovariate(0.9)), len(reglas) - 1)]
                    self.db.add(NucleoIntento(problema_sesion_id=ps.id, estudiante_id=est_id, numero=1, respuestas={},
                                              correcto=False, errores={"resultado": regla.codigo}, tiempo_ms=9000,
                                              modo_respuesta="banco", fecha=momento))
                    self.db.add(NucleoIntento(problema_sesion_id=ps.id, estudiante_id=est_id, numero=2, respuestas={},
                                              correcto=True, errores={}, tiempo_ms=5000, modo_respuesta="banco",
                                              fecha=momento + timedelta(seconds=20)))
                else:
                    self.db.add(NucleoIntento(problema_sesion_id=ps.id, estudiante_id=est_id, numero=1, respuestas={},
                                              correcto=True, errores={}, tiempo_ms=6000, modo_respuesta="banco", fecha=momento))
                if zona != ZONA_EXTENSION:
                    ultimos[lec] = ps
        await self.db.flush()
        return ultimos

    async def dominio(self, est_id: int, lec: str, ps: NucleoProblemaSesion, dominada: bool, ultima: datetime) -> None:
        self.db.add(NucleoDominio(
            estudiante_id=est_id, leccion_id=lec, estado=DOMINIO_DOMINADO if dominada else DOMINIO_EN_PROGRESO,
            fecha_inicio=INICIO, fecha_dominio=ps.fecha_fin if dominada else None, ultima_practica=ultima))
        if dominada:
            self.db.add(NucleoExperiencia(estudiante_id=est_id, tipo=XP_LECCION_DOMINADA, cantidad=50, leccion_id=lec,
                                          problema_sesion_id=ps.id, primera_vez=True, fecha=ps.fecha_fin))


async def crear() -> int:
    async with AsyncSessionLocal() as db:
        prof = (await db.execute(select(Profesor).where(Profesor.codigo_profesor == "PROF001"))).scalar_one_or_none()
        if prof is None or prof.organizacion_id is None:
            print("No existe PROF001 con organización.", file=sys.stderr)
            return 1
        org = prof.organizacion_id
        if (await db.execute(select(Salon).where(and_(Salon.organizacion_id == org, Salon.nombre == SALON)))).first():
            print(f"El salón «{SALON}» ya existe: bórralo antes con --borrar.", file=sys.stderr)
            return 1
        if (await db.execute(select(Estudiante).where(Estudiante.codigo_estudiante.like(f"{PREFIJO}%")))).first():
            print(f"Ya hay estudiantes {PREFIJO}*: bórralos antes con --borrar.", file=sys.stderr)
            return 1

        hash_ = get_password_hash(CONTRASENA)
        ests = []
        for i, nombre in enumerate(NOMBRES, start=1):
            e = Estudiante(codigo_estudiante=f"{PREFIJO}{i:02d}", password_hash=hash_, tipo_usuario="estudiante",
                           nombre_completo=nombre, organizacion_id=org)
            db.add(e)
            ests.append(e)
        await db.flush()

        salon = Salon(organizacion_id=org, nombre=SALON, grado=1)
        anterior = Salon(organizacion_id=org, nombre=SALON_ANTERIOR, grado=1)
        db.add_all([salon, anterior])
        await db.flush()
        anio = AnioLectivo(salon_id=salon.id, anio=2026, profesor_id=prof.id, estado=ANIO_ACTIVO)
        viejo = AnioLectivo(salon_id=anterior.id, anio=2025, profesor_id=prof.id, estado=ANIO_CERRADO,
                            fecha_cierre=datetime(2025, 12, 12))
        db.add_all([anio, viejo])
        await db.flush()
        for e in ests:
            db.add(Matricula(anio_lectivo_id=anio.id, estudiante_id=e.id, estado=MATRICULA_ACTIVA,
                             fecha_ingreso=datetime(2026, 3, 2)))
        for e in (ests[0], ests[6]):
            db.add(Matricula(anio_lectivo_id=viejo.id, estudiante_id=e.id, estado=MATRICULA_CERRADA,
                             fecha_ingreso=datetime(2025, 3, 3), fecha_salida=datetime(2025, 12, 12)))
        await db.flush()
        await SchoolService(db).trimestres(org, 2026)

        hab = ServicioHabilitacion(db)
        for lec in HABILITADAS:
            await hab.habilitar(anio.id, prof.id, lec, prioritaria=lec == PRIORITARIA, manual=False)

        sim = Simulador(db, anio.id)
        resumen = {}

        async def perfil(e, dominadas: list[str], en_progreso: dict[str, float], extra=(), dias=10,
                         hasta: datetime = FIN, refuerzo: list[bool] = (), ext: list[bool] = ()):
            items = []
            for lec in dominadas:
                items += [(lec, ZONA_PRIORIDAD if lec == PRIORITARIA else ZONA_NORMAL, a)
                          for a in serie(rng.randint(12, 16), 0.75, final_bueno=True)]
            for lec, valor in en_progreso.items():
                prec, n = valor if isinstance(valor, tuple) else (valor, 12 if valor < 0.6 else rng.randint(6, 9))
                items += [(lec, ZONA_PRIORIDAD if lec == PRIORITARIA else ZONA_NORMAL, a) for a in serie(n, prec)]
            items += list(extra)
            items += [(PRE_NO_HABILITADO, ZONA_REFUERZO, a) for a in refuerzo]
            items += [(EXTENSION, ZONA_EXTENSION, a) for a in ext]
            fechas = dias_de_practica(dias, hasta=hasta)
            # Refuerzo y extensión van al final (son recientes); lo demás en orden del programa
            ultimos = await sim.practica(e.id, items, fechas)
            ultima = fechas[-1]
            for lec in dominadas:
                await sim.dominio(e.id, lec, ultimos[lec], True, ultima)
            for lec in list(en_progreso) + ([PRE_NO_HABILITADO] if refuerzo else []):
                await sim.dominio(e.id, lec, ultimos[lec], False, ultima)
            resumen[e.codigo_estudiante] = (len(dominadas), len(en_progreso))

        base = HABILITADAS[:2]
        for e in ests[0:6]:                                  # dominan casi todo
            await perfil(e, HABILITADAS[:-1], {HABILITADAS[-1]: 0.7}, dias=14)
        for i, e in enumerate(ests[6:15]):                   # en progreso
            k = 2 + i % 3
            await perfil(e, HABILITADAS[:k], {HABILITADAS[k]: 0.65 + 0.03 * (i % 4), HABILITADAS[k + 1]: 0.7}, dias=9)
        for e in ests[15:17]:                                # atascados: el refuerzo no basta
            await perfil(e, base, {PRIORITARIA: 0.3}, refuerzo=[False, True, False, False, False], dias=8)
        await perfil(ests[17], base, {"g1-u04-l01": 0.35}, dias=7)              # sin refuerzo posible
        await perfil(ests[18], [], {"g1-u02-l01": (0.7, 12), "g1-u02-l02": 0.7}, dias=7)  # detrás del salón
        await perfil(ests[19], ["g1-u02-l01", "g1-u02-l02", PRIORITARIA, "g1-u05-l01"], {"g1-u04-l01": 0.8},
                     ext=[True, True, True, False, True, True, True, True, True, True], dias=10)   # sobresale
        for e in ests[20:22]:                                # en repaso: hace 20 días que no practican
            await perfil(e, ["g1-u02-l01", "g1-u02-l02", "g1-u04-l01"], {}, dias=6, hasta=FIN - timedelta(days=20))
        # ests[22:25]: sin empezar

        # Año anterior (2025, cerrado) para dos estudiantes
        sim_viejo = Simulador(db, viejo.id)
        for e in (ests[0], ests[6]):
            items = [(lec, ZONA_NORMAL, a) for lec in ("g1-u02-l01", "g1-u02-l02") for a in serie(12, 0.8, True)]
            ultimos = await sim_viejo.practica(e.id, items, dias_de_practica(5, datetime(2025, 9, 1), datetime(2025, 11, 20)))
            for lec, ps in ultimos.items():
                db.add(NucleoExperiencia(estudiante_id=e.id, tipo=XP_LECCION_DOMINADA, cantidad=50, leccion_id=lec,
                                         problema_sesion_id=ps.id, primera_vez=True, fecha=ps.fecha_fin))
        await db.commit()
        print(f"Creado «{SALON}» (año lectivo {anio.id}) con {len(ests)} estudiantes {PREFIJO}01–{PREFIJO}25 "
              f"(contraseña {CONTRASENA}) y «{SALON_ANTERIOR}» 2025 cerrado (año lectivo {viejo.id}).")
        return 0


# Núcleo primero (en orden de dependencias); luego lo que otras partes del sistema crean al usar la cuenta
_BORRAR_NUCLEO = [
    "DELETE FROM nucleo_evento WHERE problema_sesion_id IN (SELECT id FROM nucleo_problema_sesion WHERE estudiante_id = ANY(:e))",
    "DELETE FROM nucleo_intento WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_experiencia WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_problema_sesion WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_diagnostico WHERE estudiante_id = ANY(:e) OR anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_sesion WHERE estudiante_id = ANY(:e) OR anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_dominio WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_extension WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_asignacion WHERE estudiante_id = ANY(:e) OR anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_ajuste_estudiante WHERE estudiante_id = ANY(:e)",
    "DELETE FROM nucleo_alerta_oculta WHERE estudiante_id = ANY(:e) OR anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_plan_trimestre WHERE anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_prerrequisito_editado WHERE anio_lectivo_id = ANY(:a)",
    "DELETE FROM nucleo_habilitacion WHERE anio_lectivo_id = ANY(:a)",
]


async def borrar() -> int:
    async with AsyncSessionLocal() as db:
        ests = list((await db.execute(
            select(Estudiante.id).where(Estudiante.codigo_estudiante.op("~")(f"^{PREFIJO}[0-9]{{2}}$"))
        )).scalars())
        salones = list((await db.execute(select(Salon.id).where(Salon.nombre.in_([SALON, SALON_ANTERIOR])))).scalars())
        anios = list((await db.execute(select(AnioLectivo.id).where(AnioLectivo.salon_id.in_(salones))))
                     .scalars()) if salones else []
        if not ests and not salones:
            print("No hay nada que borrar.")
            return 0
        p = {"e": ests or [0], "a": anios or [0]}
        if not await borrar_dependencias(db, p):
            await db.rollback()
            return 1

        await db.execute(text("DELETE FROM anio_lectivo WHERE id = ANY(:a)"), p)
        await db.execute(text("DELETE FROM salon WHERE id = ANY(:s)"), {"s": salones or [0]})
        await db.execute(text("DELETE FROM estudiante WHERE id = ANY(:e)"), p)
        await db.execute(text("DELETE FROM usuario WHERE id = ANY(:e)"), p)
        await db.commit()
        print(f"Borrados {len(ests)} estudiantes {PREFIJO}*, {len(salones)} salones y {len(anios)} años lectivos de prueba.")
        return 0


async def borrar_dependencias(db, p: dict) -> bool:
    """Borra lo del núcleo y todo lo que apunte a los estudiantes `p["e"]` o a los años lectivos
    `p["a"]` (decimales, gamificación, grupos…), en rondas hasta que no queden dependencias.
    No borra los estudiantes, los años ni los salones. También lo usa estudiante_prueba_7a.py."""
    for sql in _BORRAR_NUCLEO:
        await db.execute(text(sql), p)
    fks = (await db.execute(text("""
        SELECT tc.table_name, kcu.column_name, ccu.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name IN ('estudiante', 'usuario', 'anio_lectivo')
          AND tc.table_name NOT IN ('estudiante', 'profesor', 'anio_lectivo')
    """))).tuples().all()
    pendientes = [(t, c, "e" if ref in ("estudiante", "usuario") else "a") for t, c, ref in fks]
    for _ in range(5):
        fallidas = []
        for tabla, columna, clave in pendientes:
            try:
                async with db.begin_nested():
                    await db.execute(text(f'DELETE FROM "{tabla}" WHERE "{columna}" = ANY(:v)'), {"v": p[clave]})
            except Exception:
                fallidas.append((tabla, columna, clave))
        if not fallidas:
            break
        pendientes = fallidas
    else:
        print(f"No se pudieron borrar: {pendientes}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Salón de prueba para el seguimiento del profesor.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--crear", action="store_true")
    grupo.add_argument("--borrar", action="store_true")
    args = parser.parse_args()
    return asyncio.run(crear() if args.crear else borrar())


if __name__ == "__main__":
    sys.exit(main())
