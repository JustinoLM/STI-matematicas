"""
Helpers de pruebas para la organización escolar: crean organización, profesor, salón,
año lectivo y matrículas directamente en la base (sin pasar por la API).
"""

from datetime import date
from itertools import count
from typing import Iterable, Optional

from app.models.organization import Organizacion
from app.models.school import ANIO_ACTIVO, MATRICULA_ACTIVA, AnioLectivo, Matricula, Salon
from app.models.user import Profesor

_secuencia = count(1)


async def crear_organizacion(db, nombre: Optional[str] = None) -> Organizacion:
    n = next(_secuencia)
    org = Organizacion(nombre=nombre or f"Escuela {n}", codigo=f"ORG{n}")
    db.add(org)
    await db.flush()
    return org


async def crear_profesor(db, organizacion_id: Optional[int], codigo: Optional[str] = None) -> Profesor:
    n = next(_secuencia)
    prof = Profesor(
        codigo_profesor=codigo or f"PROF{n}", password_hash="x", tipo_usuario="profesor",
        nombre_completo=f"Profesor {n}", organizacion_id=organizacion_id,
    )
    db.add(prof)
    await db.flush()
    return prof


async def salon_con_estudiantes(
    db,
    estudiantes_ids: Iterable[int] = (),
    *,
    profesor: Optional[Profesor] = None,
    organizacion_id: Optional[int] = None,
    nombre: Optional[str] = None,
    grado: int = 1,
    anio: Optional[int] = None,
) -> tuple[Profesor, AnioLectivo]:
    """Crea un salón con su año lectivo activo y matricula a los estudiantes indicados."""
    if organizacion_id is None:
        organizacion_id = profesor.organizacion_id if profesor and profesor.organizacion_id else (await crear_organizacion(db)).id
    if profesor is None:
        profesor = await crear_profesor(db, organizacion_id)
    salon = Salon(organizacion_id=organizacion_id, nombre=nombre or f"S{next(_secuencia)}", grado=grado)
    db.add(salon)
    await db.flush()
    al = AnioLectivo(salon_id=salon.id, anio=anio or date.today().year, profesor_id=profesor.id, estado=ANIO_ACTIVO)
    db.add(al)
    await db.flush()
    for est_id in estudiantes_ids:
        db.add(Matricula(anio_lectivo_id=al.id, estudiante_id=est_id, estado=MATRICULA_ACTIVA))
    await db.flush()
    return profesor, al
