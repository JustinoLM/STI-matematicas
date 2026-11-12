"""
Organización escolar: salones, años lectivos, matrículas, grupos del salón y trimestres.

Reglas (docs/DISENO_MODULAR.md, sección 2 → Organización):
- El salón es fijo dentro de la organización ("1A") y tiene grado de 1 a 6.
- El año lectivo del salón tiene un profesor. Un salón tiene como máximo un año activo.
- Un estudiante tiene como máximo una matrícula activa (salón activo) en todo el sistema.
- Un año cerrado es de solo lectura: estudiantes, grupos, configuración y desafíos.
- Los trimestres son por organización y año; los edita el administrador.
- Un estudiante sin salón activo no puede practicar.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.adaptive import PerfilEstudiante
from app.models.challenge import DESAFIO_ACTIVO, DESAFIO_NO_COMPLETADO, DesafioGrupal
from app.models.group import EstudianteGrupo, Grupo
from app.models.school import (
    ANIO_ACTIVO,
    ANIO_CERRADO,
    MATRICULA_ACTIVA,
    MATRICULA_CERRADA,
    MATRICULA_RETIRADA,
    AnioLectivo,
    Matricula,
    Salon,
    Trimestre,
)
from app.models.user import Estudiante, Profesor

SEMANAS_POR_TRIMESTRE = 13
SEMANAS_DE_VACACIONES = 1
MENSAJE_SIN_SALON = (
    "Todavía no estás en ningún salón. Consulta a tu profesor para que te asigne a uno."
)


# ─── Errores ─────────────────────────────────────────────────────────────────

class ErrorSalon(Exception):
    """Error de una regla de la organización escolar; el router lo traduce a HTTP."""

    status_code = 400
    codigo: Optional[str] = None

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorSalon):
    status_code = 404


class Conflicto(ErrorSalon):
    status_code = 409


class AnioCerrado(Conflicto):
    codigo = "ANIO_CERRADO"

    def __init__(self, mensaje: str = "El año lectivo está cerrado: es de solo lectura."):
        super().__init__(mensaje)


class SinSalon(ErrorSalon):
    status_code = 403
    codigo = "SIN_SALON"

    def __init__(self, mensaje: str = MENSAJE_SIN_SALON):
        super().__init__(mensaje)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def anio_actual() -> int:
    """Año lectivo en curso: en Panamá coincide con el año calendario (marzo a diciembre)."""
    return date.today().year


def trimestres_por_defecto(anio: int) -> list[tuple[date, date]]:
    """
    Fechas por defecto de los 3 trimestres de un año.

    El año empieza el primer lunes de marzo; cada trimestre dura 13 semanas (de lunes a
    viernes) y entre trimestres hay 1 semana de vacaciones. Con 41 semanas en total, el año
    termina a mediados de diciembre (2026: 2 mar–29 may, 8 jun–4 sep, 14 sep–11 dic).
    """
    primero_marzo = date(anio, 3, 1)
    inicio = primero_marzo + timedelta(days=(7 - primero_marzo.weekday()) % 7)
    fechas = []
    for _ in range(3):
        fin = inicio + timedelta(weeks=SEMANAS_POR_TRIMESTRE) - timedelta(days=3)  # viernes
        fechas.append((inicio, fin))
        inicio = inicio + timedelta(weeks=SEMANAS_POR_TRIMESTRE + SEMANAS_DE_VACACIONES)
    return fechas


def normalizar_nombre_salon(nombre: str) -> str:
    return " ".join(nombre.split()).upper()


# ─── Servicio ────────────────────────────────────────────────────────────────

class SchoolService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Matrícula del estudiante ────────────────────────────────────────────

    async def matricula_activa(self, estudiante_id: int) -> Optional[Matricula]:
        """Matrícula activa del estudiante (con año lectivo, salón y profesor), o None."""
        result = await self.db.execute(
            select(Matricula)
            .where(and_(Matricula.estudiante_id == estudiante_id, Matricula.estado == MATRICULA_ACTIVA))
            .options(
                selectinload(Matricula.anio_lectivo).selectinload(AnioLectivo.salon),
                selectinload(Matricula.anio_lectivo).selectinload(AnioLectivo.profesor),
            )
        )
        return result.scalar_one_or_none()

    async def exigir_salon(self, estudiante_id: int) -> Matricula:
        """Matrícula activa del estudiante; si no tiene salón, lanza SinSalon."""
        matricula = await self.matricula_activa(estudiante_id)
        if matricula is None:
            raise SinSalon()
        return matricula

    async def info_salon_estudiante(self, estudiante_id: int) -> Optional[dict]:
        """Salón, grado, año y profesor del estudiante, o None si no tiene salón."""
        matricula = await self.matricula_activa(estudiante_id)
        if matricula is None:
            return None
        al = matricula.anio_lectivo
        return {
            "anio_lectivo_id": al.id,
            "salon_id": al.salon_id,
            "salon_nombre": al.salon.nombre,
            "grado": al.salon.grado,
            "anio": al.anio,
            "profesor_nombre": al.profesor.nombre_completo,
        }

    async def salones_de_estudiantes(self, estudiantes_ids: Sequence[int]) -> dict[int, dict]:
        """{estudiante_id: {salon_nombre, grado, anio, anio_lectivo_id}} de las matrículas activas."""
        if not estudiantes_ids:
            return {}
        result = await self.db.execute(
            select(Matricula.estudiante_id, Salon.nombre, Salon.grado, AnioLectivo.anio, AnioLectivo.id)
            .join(AnioLectivo, AnioLectivo.id == Matricula.anio_lectivo_id)
            .join(Salon, Salon.id == AnioLectivo.salon_id)
            .where(and_(Matricula.estudiante_id.in_(list(estudiantes_ids)), Matricula.estado == MATRICULA_ACTIVA))
        )
        return {
            eid: {"salon_nombre": nombre, "grado": grado, "anio": anio, "anio_lectivo_id": al_id}
            for eid, nombre, grado, anio, al_id in result.all()
        }

    # ── Trimestres ──────────────────────────────────────────────────────────

    async def trimestres(self, organizacion_id: int, anio: int, crear: bool = True) -> list[Trimestre]:
        """Trimestres de la organización en el año; si faltan, se crean con las fechas por defecto."""
        result = await self.db.execute(
            select(Trimestre)
            .where(and_(Trimestre.organizacion_id == organizacion_id, Trimestre.anio == anio))
            .order_by(Trimestre.numero)
        )
        existentes = list(result.scalars().all())
        if len(existentes) == 3 or not crear:
            return existentes
        por_numero = {t.numero: t for t in existentes}
        for numero, (inicio, fin) in enumerate(trimestres_por_defecto(anio), start=1):
            if numero not in por_numero:
                t = Trimestre(
                    organizacion_id=organizacion_id, anio=anio, numero=numero,
                    fecha_inicio=inicio, fecha_fin=fin,
                )
                self.db.add(t)
                por_numero[numero] = t
        await self.db.flush()
        return [por_numero[n] for n in (1, 2, 3)]

    async def actualizar_trimestres(
        self, organizacion_id: int, anio: int, fechas: list[tuple[date, date]]
    ) -> list[Trimestre]:
        """Reemplaza las fechas de los 3 trimestres (validando orden y que no se solapen)."""
        if len(fechas) != 3:
            raise ErrorSalon("Debes indicar las fechas de los 3 trimestres.")
        anterior_fin: Optional[date] = None
        for numero, (inicio, fin) in enumerate(fechas, start=1):
            if inicio > fin:
                raise ErrorSalon(f"El trimestre {numero} termina antes de empezar.")
            if inicio.year != anio or fin.year != anio:
                raise ErrorSalon(f"Las fechas del trimestre {numero} deben estar dentro de {anio}.")
            if anterior_fin is not None and inicio <= anterior_fin:
                raise ErrorSalon(f"El trimestre {numero} debe empezar después de que termine el anterior.")
            anterior_fin = fin
        trimestres = await self.trimestres(organizacion_id, anio)
        for t, (inicio, fin) in zip(trimestres, fechas):
            t.fecha_inicio, t.fecha_fin = inicio, fin
        await self.db.flush()
        return trimestres

    # ── Salones del profesor ────────────────────────────────────────────────

    async def anios_del_profesor(self, profesor_id: int) -> list[AnioLectivo]:
        """Años lectivos del profesor (activos primero, luego los más recientes)."""
        result = await self.db.execute(
            select(AnioLectivo)
            .where(AnioLectivo.profesor_id == profesor_id)
            .options(selectinload(AnioLectivo.salon))
            .order_by((AnioLectivo.estado == ANIO_ACTIVO).desc(), AnioLectivo.anio.desc(), AnioLectivo.id)
        )
        return list(result.scalars().all())

    async def abrir_salon(self, profesor: Profesor, nombre: str, grado: int) -> AnioLectivo:
        """
        Crea el salón (si no existe en la organización) y abre su año lectivo actual con el
        profesor. Si el salón ya existe, se reutiliza: su id es permanente.
        """
        if not profesor.organizacion_id:
            raise Conflicto("No tienes una organización asignada. Consulta al administrador.")
        nombre = normalizar_nombre_salon(nombre)
        if not nombre:
            raise ErrorSalon("El nombre del salón no puede estar vacío.")
        if not 1 <= grado <= 6:
            raise ErrorSalon("El grado debe estar entre 1 y 6.")

        salon = (await self.db.execute(
            select(Salon).where(and_(Salon.organizacion_id == profesor.organizacion_id, Salon.nombre == nombre))
        )).scalar_one_or_none()
        if salon is None:
            salon = Salon(organizacion_id=profesor.organizacion_id, nombre=nombre, grado=grado)
            self.db.add(salon)
            await self.db.flush()
        elif salon.grado != grado:
            raise Conflicto(f"El salón {nombre} ya existe y es de {salon.grado}.º grado.")

        anio = anio_actual()
        activo = (await self.db.execute(
            select(AnioLectivo)
            .where(and_(AnioLectivo.salon_id == salon.id, AnioLectivo.estado == ANIO_ACTIVO))
            .options(selectinload(AnioLectivo.profesor))
        )).scalar_one_or_none()
        if activo is not None:
            if activo.profesor_id == profesor.id:
                raise Conflicto(f"Ya tienes abierto el salón {nombre} en {activo.anio}.")
            raise Conflicto(
                f"El salón {nombre} ya está abierto en {activo.anio} con "
                f"{activo.profesor.nombre_completo}."
            )
        existente = (await self.db.execute(
            select(AnioLectivo).where(and_(AnioLectivo.salon_id == salon.id, AnioLectivo.anio == anio))
        )).scalar_one_or_none()
        if existente is not None:
            raise Conflicto(f"El año {anio} del salón {nombre} ya se cerró.")

        al = AnioLectivo(salon_id=salon.id, anio=anio, profesor_id=profesor.id, estado=ANIO_ACTIVO)
        self.db.add(al)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflicto(f"El salón {nombre} ya está abierto este año.")
        await self.trimestres(profesor.organizacion_id, anio)
        await self.db.refresh(al, attribute_names=["salon"])
        return al

    async def anio_del_profesor(
        self, anio_lectivo_id: int, profesor_id: int, para_escribir: bool = False
    ) -> AnioLectivo:
        """Año lectivo del profesor. Con para_escribir=True, falla si está cerrado."""
        al = (await self.db.execute(
            select(AnioLectivo)
            .where(and_(AnioLectivo.id == anio_lectivo_id, AnioLectivo.profesor_id == profesor_id))
            .options(selectinload(AnioLectivo.salon))
        )).scalar_one_or_none()
        if al is None:
            raise NoEncontrado("Salón no encontrado.")
        if para_escribir and al.estado != ANIO_ACTIVO:
            raise AnioCerrado()
        return al

    # ── Estudiantes del salón ───────────────────────────────────────────────

    async def matricular(self, anio_lectivo_id: int, estudiante_id: int, profesor: Profesor) -> Matricula:
        """Asigna el estudiante al salón. Rechaza si ya está activo en otro salón."""
        al = await self.anio_del_profesor(anio_lectivo_id, profesor.id, para_escribir=True)
        estudiante = (await self.db.execute(
            select(Estudiante).where(and_(
                Estudiante.id == estudiante_id,
                Estudiante.organizacion_id == al.salon.organizacion_id,
            ))
        )).scalar_one_or_none()
        if estudiante is None:
            raise NoEncontrado("Estudiante no encontrado en tu organización.")

        activa = await self.matricula_activa(estudiante_id)
        if activa is not None:
            if activa.anio_lectivo_id == al.id:
                return activa
            otro = activa.anio_lectivo
            raise Conflicto(
                f"{estudiante.nombre_completo} ya está en el salón {otro.salon.nombre} ({otro.anio}) "
                f"con {otro.profesor.nombre_completo}. Ese profesor debe quitarlo primero."
            )

        matricula = (await self.db.execute(
            select(Matricula).where(and_(
                Matricula.anio_lectivo_id == al.id, Matricula.estudiante_id == estudiante_id
            ))
        )).scalar_one_or_none()
        if matricula is None:
            matricula = Matricula(anio_lectivo_id=al.id, estudiante_id=estudiante_id, estado=MATRICULA_ACTIVA)
            self.db.add(matricula)
        else:
            matricula.estado = MATRICULA_ACTIVA
            matricula.fecha_ingreso = datetime.utcnow()
            matricula.fecha_salida = None
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise Conflicto(f"{estudiante.nombre_completo} ya está en otro salón.")

        tiene_perfil = (await self.db.execute(
            select(PerfilEstudiante.estudiante_id).where(PerfilEstudiante.estudiante_id == estudiante_id)
        )).first()
        if not tiene_perfil:
            self.db.add(PerfilEstudiante(estudiante_id=estudiante_id))
            await self.db.flush()
        return matricula

    async def retirar(self, anio_lectivo_id: int, estudiante_id: int, profesor_id: int) -> None:
        """Quita al estudiante del salón (la matrícula queda como retirada) y de sus grupos."""
        al = await self.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        matricula = (await self.db.execute(
            select(Matricula).where(and_(
                Matricula.anio_lectivo_id == al.id,
                Matricula.estudiante_id == estudiante_id,
                Matricula.estado == MATRICULA_ACTIVA,
            ))
        )).scalar_one_or_none()
        if matricula is None:
            raise NoEncontrado("El estudiante no está en este salón.")
        matricula.estado = MATRICULA_RETIRADA
        matricula.fecha_salida = datetime.utcnow()
        grupos_ids = select(Grupo.id).where(Grupo.anio_lectivo_id == al.id)
        await self.db.execute(
            update(EstudianteGrupo)
            .where(and_(EstudianteGrupo.estudiante_id == estudiante_id, EstudianteGrupo.grupo_id.in_(grupos_ids)))
            .values(activo=False)
        )
        await self.db.flush()

    async def estudiantes_del_anio(self, anio_lectivo_id: int) -> list[tuple[Estudiante, Matricula, Optional[PerfilEstudiante]]]:
        """Estudiantes del año lectivo: los activos o, si el año está cerrado, los que lo cerraron."""
        result = await self.db.execute(
            select(Estudiante, Matricula, PerfilEstudiante)
            .join(Matricula, Matricula.estudiante_id == Estudiante.id)
            .outerjoin(PerfilEstudiante, PerfilEstudiante.estudiante_id == Estudiante.id)
            .where(and_(
                Matricula.anio_lectivo_id == anio_lectivo_id,
                Matricula.estado.in_([MATRICULA_ACTIVA, MATRICULA_CERRADA]),
            ))
            .order_by(Estudiante.nombre_completo)
        )
        return [tuple(row) for row in result.all()]

    async def ids_estudiantes_del_anio(self, anio_lectivo_id: int) -> list[int]:
        return [e.id for e, _, _ in await self.estudiantes_del_anio(anio_lectivo_id)]

    async def ids_estudiantes_del_profesor(self, profesor_id: int) -> list[int]:
        """Estudiantes con matrícula activa en los salones activos del profesor."""
        result = await self.db.execute(
            select(Matricula.estudiante_id)
            .join(AnioLectivo, AnioLectivo.id == Matricula.anio_lectivo_id)
            .where(and_(
                AnioLectivo.profesor_id == profesor_id,
                AnioLectivo.estado == ANIO_ACTIVO,
                Matricula.estado == MATRICULA_ACTIVA,
            ))
        )
        return [row[0] for row in result.all()]

    async def candidatos(self, anio_lectivo_id: int, profesor_id: int, q: Optional[str] = None) -> list[dict]:
        """Estudiantes de la organización, indicando en qué salón activo está cada uno."""
        al = await self.anio_del_profesor(anio_lectivo_id, profesor_id)
        stmt = select(Estudiante).where(Estudiante.organizacion_id == al.salon.organizacion_id)
        if q:
            patron = f"%{q.strip()}%"
            stmt = stmt.where(or_(Estudiante.nombre_completo.ilike(patron), Estudiante.codigo_estudiante.ilike(patron)))
        estudiantes = list((await self.db.execute(stmt.order_by(Estudiante.nombre_completo))).scalars().all())
        salones = await self.salones_de_estudiantes([e.id for e in estudiantes])
        return [
            {
                "id": e.id,
                "codigo_estudiante": e.codigo_estudiante,
                "nombre_completo": e.nombre_completo,
                "salon_actual": salones.get(e.id, {}).get("salon_nombre"),
                "en_este_salon": salones.get(e.id, {}).get("anio_lectivo_id") == al.id,
            }
            for e in estudiantes
        ]

    # ── Grupos del salón ────────────────────────────────────────────────────

    async def crear_grupo(self, anio_lectivo_id: int, profesor_id: int, nombre: str) -> Grupo:
        al = await self.anio_del_profesor(anio_lectivo_id, profesor_id, para_escribir=True)
        nombre = " ".join(nombre.split())
        if not nombre:
            raise ErrorSalon("El nombre del grupo no puede estar vacío.")
        repetido = (await self.db.execute(
            select(Grupo.id).where(and_(Grupo.anio_lectivo_id == al.id, Grupo.nombre == nombre))
        )).first()
        if repetido:
            raise Conflicto(f"Ya existe un grupo llamado {nombre} en este salón.")
        grupo = Grupo(anio_lectivo_id=al.id, nombre=nombre, activo=True)
        self.db.add(grupo)
        await self.db.flush()
        return grupo

    async def grupos_del_anio(self, anio_lectivo_id: int) -> list[Grupo]:
        result = await self.db.execute(
            select(Grupo)
            .where(and_(Grupo.anio_lectivo_id == anio_lectivo_id, Grupo.activo == True))  # noqa: E712
            .options(selectinload(Grupo.estudiantes))
            .order_by(Grupo.nombre)
        )
        return list(result.scalars().all())

    async def grupo_del_profesor(self, grupo_id: int, profesor_id: int, para_escribir: bool = False) -> Grupo:
        grupo = (await self.db.execute(
            select(Grupo)
            .join(AnioLectivo, AnioLectivo.id == Grupo.anio_lectivo_id)
            .where(and_(Grupo.id == grupo_id, Grupo.activo == True, AnioLectivo.profesor_id == profesor_id))  # noqa: E712
            .options(
                selectinload(Grupo.estudiantes),
                selectinload(Grupo.anio_lectivo).selectinload(AnioLectivo.salon),
            )
        )).scalar_one_or_none()
        if grupo is None:
            raise NoEncontrado("Grupo no encontrado.")
        if para_escribir and grupo.anio_lectivo.estado != ANIO_ACTIVO:
            raise AnioCerrado()
        return grupo

    async def agregar_a_grupo(self, grupo_id: int, estudiante_id: int, profesor_id: int) -> None:
        """Agrega al grupo un estudiante matriculado en el mismo salón."""
        grupo = await self.grupo_del_profesor(grupo_id, profesor_id, para_escribir=True)
        matriculado = (await self.db.execute(
            select(Matricula.id).where(and_(
                Matricula.anio_lectivo_id == grupo.anio_lectivo_id,
                Matricula.estudiante_id == estudiante_id,
                Matricula.estado == MATRICULA_ACTIVA,
            ))
        )).first()
        if not matriculado:
            raise ErrorSalon("El estudiante no está en este salón: asígnalo al salón primero.")
        relacion = (await self.db.execute(
            select(EstudianteGrupo).where(and_(
                EstudianteGrupo.grupo_id == grupo_id, EstudianteGrupo.estudiante_id == estudiante_id
            ))
        )).scalar_one_or_none()
        if relacion is None:
            self.db.add(EstudianteGrupo(grupo_id=grupo_id, estudiante_id=estudiante_id, activo=True))
        else:
            relacion.activo = True
        await self.db.flush()

    async def quitar_de_grupo(self, grupo_id: int, estudiante_id: int, profesor_id: int) -> None:
        await self.grupo_del_profesor(grupo_id, profesor_id, para_escribir=True)
        await self.db.execute(
            update(EstudianteGrupo)
            .where(and_(EstudianteGrupo.grupo_id == grupo_id, EstudianteGrupo.estudiante_id == estudiante_id))
            .values(activo=False)
        )
        await self.db.flush()

    async def eliminar_grupo(self, grupo_id: int, profesor_id: int) -> None:
        """Desactiva el grupo (no se borra: puede tener desafíos con historial)."""
        grupo = await self.grupo_del_profesor(grupo_id, profesor_id, para_escribir=True)
        grupo.activo = False
        await self.db.flush()

    # ── Cierre del año lectivo ──────────────────────────────────────────────

    async def cerrar_anio(self, organizacion_id: int, anio: int) -> dict:
        """
        Cierra todos los años lectivos activos de la organización en ese año: quedan de solo
        lectura con sus grupos; las matrículas activas pasan a "cerrada" y los desafíos sin
        terminar a "no_completado" (los puntos ya otorgados se conservan). No se borra nada.
        """
        anios = list((await self.db.execute(
            select(AnioLectivo)
            .join(Salon, Salon.id == AnioLectivo.salon_id)
            .where(and_(
                Salon.organizacion_id == organizacion_id,
                AnioLectivo.anio == anio,
                AnioLectivo.estado == ANIO_ACTIVO,
            ))
        )).scalars().all())
        ids = [al.id for al in anios]
        ahora = datetime.utcnow()
        matriculas = desafios = 0
        if ids:
            matriculas = (await self.db.execute(
                update(Matricula)
                .where(and_(Matricula.anio_lectivo_id.in_(ids), Matricula.estado == MATRICULA_ACTIVA))
                .values(estado=MATRICULA_CERRADA, fecha_salida=ahora)
            )).rowcount
            desafios = (await self.db.execute(
                update(DesafioGrupal)
                .where(and_(DesafioGrupal.anio_lectivo_id.in_(ids), DesafioGrupal.estado == DESAFIO_ACTIVO))
                .values(estado=DESAFIO_NO_COMPLETADO)
            )).rowcount
            for al in anios:
                al.estado = ANIO_CERRADO
                al.fecha_cierre = ahora
        await self.db.flush()
        return {"anios_cerrados": len(ids), "matriculas_cerradas": matriculas, "desafios_no_completados": desafios}

    # ── Vista del administrador ─────────────────────────────────────────────

    async def salones_de_organizacion(self, organizacion_id: int) -> list[dict]:
        """Salones de la organización con su año lectivo más reciente."""
        salones = list((await self.db.execute(
            select(Salon)
            .where(Salon.organizacion_id == organizacion_id)
            .options(selectinload(Salon.anios_lectivos).selectinload(AnioLectivo.profesor))
            .order_by(Salon.grado, Salon.nombre)
        )).scalars().all())
        conteos = dict((await self.db.execute(
            select(Matricula.anio_lectivo_id, func.count(Matricula.id))
            .where(Matricula.estado.in_([MATRICULA_ACTIVA, MATRICULA_CERRADA]))
            .group_by(Matricula.anio_lectivo_id)
        )).all())
        filas = []
        for s in salones:
            anios = sorted(s.anios_lectivos, key=lambda a: a.anio, reverse=True)
            ultimo = anios[0] if anios else None
            filas.append({
                "salon_id": s.id,
                "nombre": s.nombre,
                "grado": s.grado,
                "anio_lectivo_id": ultimo.id if ultimo else None,
                "anio": ultimo.anio if ultimo else None,
                "estado": ultimo.estado if ultimo else None,
                "profesor_nombre": ultimo.profesor.nombre_completo if ultimo else None,
                "total_estudiantes": conteos.get(ultimo.id, 0) if ultimo else 0,
            })
        return filas
