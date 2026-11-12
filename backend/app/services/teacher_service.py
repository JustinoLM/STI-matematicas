"""Service para operaciones del profesor."""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import (
    AlertaEstudiante,
    EstadoSesion,
    PerfilEstudiante,
    SesionPractica,
    TipoAlerta,
)
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.group import EstudianteGrupo, Grupo
from app.models.practice_config import ConfiguracionPractica
from app.models.problem import Intento
from app.models.school import ANIO_ACTIVO, AnioLectivo
from app.models.user import Estudiante
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.teacher import (
    AlertaEstudianteResponse,
    ConfiguracionPracticaCreate,
    ConfiguracionPracticaResponse,
    DesafioGrupalCreate,
    DesafioGrupalDetalle,
    EstadisticasGrupo,
    EstudianteEnGrupo,
    GrupoCreate,
    GrupoDetalle,
    GrupoResumen,
    ProgresoGrupoDesafio,
)
from app.services.desafios_service import NOMBRE_EQUIPO_SALON, calcular_progreso, miembros_equipo
from app.services.school_service import AnioCerrado, ErrorSalon, NoEncontrado, SchoolService


class TeacherService:
    """Service para APIs del profesor."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TeacherRepository(db)
        self.school = SchoolService(db)

    # ==================== GRUPOS DEL SALÓN ====================

    async def crear_grupo(self, profesor_id: int, anio_lectivo_id: int, data: GrupoCreate) -> GrupoDetalle:
        """Crea un grupo dentro del salón (año lectivo activo) del profesor."""
        grupo = await self.school.crear_grupo(anio_lectivo_id, profesor_id, data.nombre)
        await self.db.commit()
        detalle = await self.get_grupo_detalle(grupo.id, profesor_id)
        assert detalle is not None
        return detalle

    async def get_grupos(self, profesor_id: int, anio_lectivo_id: Optional[int] = None) -> List[GrupoResumen]:
        """Grupos de los salones del profesor (opcionalmente de un solo año lectivo)."""
        stmt = (
            select(Grupo, AnioLectivo)
            .join(AnioLectivo, AnioLectivo.id == Grupo.anio_lectivo_id)
            .where(and_(AnioLectivo.profesor_id == profesor_id, Grupo.activo == True))  # noqa: E712
            .order_by((AnioLectivo.estado == ANIO_ACTIVO).desc(), AnioLectivo.anio.desc(), Grupo.nombre)
        )
        if anio_lectivo_id is not None:
            stmt = stmt.where(Grupo.anio_lectivo_id == anio_lectivo_id)
        filas = (await self.db.execute(stmt)).all()

        resumenes = []
        for grupo, al in filas:
            await self.db.refresh(al, attribute_names=["salon"])
            miembros = (await self.db.execute(
                select(EstudianteGrupo.estudiante_id).where(and_(
                    EstudianteGrupo.grupo_id == grupo.id, EstudianteGrupo.activo == True  # noqa: E712
                ))
            )).all()
            estudiantes_ids = [row[0] for row in miembros]

            promedio = 0.0
            if estudiantes_ids:
                result = await self.db.execute(
                    select(func.avg(PerfilEstudiante.precision_ultimos_15))
                    .where(PerfilEstudiante.estudiante_id.in_(estudiantes_ids))
                )
                promedio = float(result.scalar() or 0.0)

            problemas_hoy = await self.repo.get_problemas_resueltos_hoy(estudiantes_ids) if estudiantes_ids else 0

            resumenes.append(GrupoResumen(
                id=grupo.id,
                nombre=grupo.nombre,
                activo=grupo.activo,
                anio_lectivo_id=al.id,
                salon_nombre=al.salon.nombre,
                anio=al.anio,
                cerrado=al.estado != ANIO_ACTIVO,
                estudiantes_ids=estudiantes_ids,
                cantidad_estudiantes=len(estudiantes_ids),
                promedio_precision=round(promedio * 100, 2),
                problemas_resueltos_hoy=problemas_hoy,
            ))

        return resumenes

    async def get_grupo_detalle(self, grupo_id: int, profesor_id: int) -> Optional[GrupoDetalle]:
        """Detalle del grupo con sus estudiantes, o None si no es del profesor."""
        try:
            grupo = await self.school.grupo_del_profesor(grupo_id, profesor_id)
        except NoEncontrado:
            return None

        estudiantes_lista = []
        for rel in grupo.estudiantes:
            if not rel.activo:
                continue
            row = (await self.db.execute(
                select(Estudiante, PerfilEstudiante)
                .outerjoin(PerfilEstudiante, Estudiante.id == PerfilEstudiante.estudiante_id)
                .where(Estudiante.id == rel.estudiante_id)
            )).first()
            if row:
                estudiante, perfil = row
                estudiantes_lista.append(EstudianteEnGrupo(
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_completo=estudiante.nombre_completo,
                    nivel_actual=perfil.nivel_actual if perfil else 1,
                    precision_ultimos_15=float(perfil.precision_ultimos_15 or 0.0) * 100 if perfil else 0.0,
                    fecha_ingreso=rel.fecha_ingreso,
                    activo=rel.activo,
                ))

        al = grupo.anio_lectivo
        return GrupoDetalle(
            id=grupo.id,
            nombre=grupo.nombre,
            activo=grupo.activo,
            anio_lectivo_id=al.id,
            salon_nombre=al.salon.nombre,
            anio=al.anio,
            cerrado=al.estado != ANIO_ACTIVO,
            cantidad_estudiantes=len(estudiantes_lista),
            estudiantes=estudiantes_lista,
        )

    async def agregar_estudiante(self, grupo_id: int, estudiante_id: int, profesor_id: int):
        """Agrega al grupo un estudiante del mismo salón."""
        await self.school.agregar_a_grupo(grupo_id, estudiante_id, profesor_id)
        await self.db.commit()

    async def remover_estudiante(self, grupo_id: int, estudiante_id: int, profesor_id: int):
        """Quita al estudiante del grupo (sigue en el salón)."""
        await self.school.quitar_de_grupo(grupo_id, estudiante_id, profesor_id)
        await self.db.commit()

    async def eliminar_grupo(self, grupo_id: int, profesor_id: int):
        """Desactiva el grupo. Solo su profesor, y solo con el año lectivo activo."""
        await self.school.eliminar_grupo(grupo_id, profesor_id)
        await self.db.commit()

    # ==================== CONFIGURACIÓN ====================

    async def crear_configuracion(
        self,
        profesor_id: int,
        data: ConfiguracionPracticaCreate
    ) -> ConfiguracionPracticaResponse:
        """Aplica una configuración de práctica (decimales) al salón."""
        al = await self.school.anio_del_profesor(data.anio_lectivo_id, profesor_id, para_escribir=True)

        config = ConfiguracionPractica(
            anio_lectivo_id=al.id,
            aplicada_por_profesor_id=profesor_id,
            operaciones_permitidas=data.operaciones_permitidas,
            niveles_permitidos=data.niveles_permitidos,
            rango_min=data.rango_min,
            rango_max=data.rango_max,
            decimales_maximos=data.decimales_maximos,
            pistas_habilitadas=data.pistas_habilitadas
        )

        config = await self.repo.create_configuracion(config)
        await self.db.commit()

        return ConfiguracionPracticaResponse.model_validate(config)

    async def get_configuracion_activa(
        self, anio_lectivo_id: int, profesor_id: int
    ) -> Optional[ConfiguracionPracticaResponse]:
        """Configuración activa del salón (también la de un año ya cerrado, de solo lectura)."""
        al = await self.school.anio_del_profesor(anio_lectivo_id, profesor_id)
        config = await self.repo.get_configuracion_activa(al.id)
        if not config:
            return None
        return ConfiguracionPracticaResponse.model_validate(config)

    # ==================== DESAFÍOS ====================

    async def _calcular_progreso_desafio(self, desafio: DesafioGrupal, grupo_id: Optional[int]) -> int:
        """Progreso real del equipo (grupo o salón completo) en el desafío."""
        miembros = await miembros_equipo(self.db, desafio, grupo_id)
        return await calcular_progreso(self.db, desafio, miembros)

    async def _detalle_desafio(self, desafio: DesafioGrupal, ahora: datetime) -> DesafioGrupalDetalle:
        """Detalle con el progreso de cada equipo.

        Estados mostrados:
        - completado=True → todos los equipos alcanzaron el objetivo
        - vencido=True → la fecha límite pasó sin completarse
        - estado="no_completado" → se cerró con el año lectivo sin terminar
        """
        al = (await self.db.execute(
            select(AnioLectivo).where(AnioLectivo.id == desafio.anio_lectivo_id)
        )).scalar_one()
        await self.db.refresh(al, attribute_names=["salon"])
        relaciones = (await self.db.execute(
            select(GrupoDesafio).where(GrupoDesafio.desafio_id == desafio.id).order_by(GrupoDesafio.id)
        )).scalars().all()

        progreso_grupos = []
        todos_completados = len(relaciones) > 0
        for rel in relaciones:
            if rel.grupo_id is None:
                nombre = NOMBRE_EQUIPO_SALON
            else:
                grupo = (await self.db.execute(select(Grupo).where(Grupo.id == rel.grupo_id))).scalar_one()
                nombre = grupo.nombre
            progreso_real = await self._calcular_progreso_desafio(desafio, rel.grupo_id)
            completado_equipo = progreso_real >= desafio.objetivo_cantidad
            if not completado_equipo:
                todos_completados = False
            progreso_grupos.append(ProgresoGrupoDesafio(
                grupo_id=rel.grupo_id,
                nombre_grupo=nombre,
                progreso_actual=progreso_real,
                objetivo_cantidad=desafio.objetivo_cantidad,
                porcentaje=min(round((progreso_real / desafio.objetivo_cantidad) * 100, 1), 100.0),
                completado=completado_equipo,
            ))

        vencido = (
            desafio.fecha_limite is not None
            and desafio.fecha_limite < ahora
            and not todos_completados
        )
        return DesafioGrupalDetalle(
            id=desafio.id,
            profesor_id=desafio.profesor_id,
            anio_lectivo_id=al.id,
            salon_nombre=al.salon.nombre,
            anio=al.anio,
            estado=desafio.estado,
            nombre=desafio.nombre,
            descripcion=desafio.descripcion,
            tipo=desafio.tipo,
            objetivo_cantidad=desafio.objetivo_cantidad,
            parametro_adicional=desafio.parametro_adicional,
            recompensa_texto=desafio.recompensa_texto,
            recompensa_puntos=desafio.recompensa_puntos,
            fecha_creacion=desafio.fecha_creacion,
            fecha_limite=desafio.fecha_limite,
            completado=todos_completados,
            vencido=vencido,
            eliminado=desafio.eliminado,
            progreso_grupos=progreso_grupos,
        )

    async def crear_desafio_grupal(
        self,
        profesor_id: int,
        data: DesafioGrupalCreate
    ) -> DesafioGrupalDetalle:
        """Crea un desafío dentro de un salón: para algunos de sus grupos o para el salón completo."""
        al = await self.school.anio_del_profesor(data.anio_lectivo_id, profesor_id, para_escribir=True)

        grupos_ids = sorted(set(data.grupos_ids))
        if grupos_ids:
            validos = set((await self.db.execute(
                select(Grupo.id).where(and_(
                    Grupo.id.in_(grupos_ids),
                    Grupo.anio_lectivo_id == al.id,
                    Grupo.activo == True,  # noqa: E712
                ))
            )).scalars().all())
            if validos != set(grupos_ids):
                raise ErrorSalon("Los grupos del desafío deben ser del mismo salón.")
        equipos: List[Optional[int]] = list(grupos_ids) if grupos_ids else [None]

        desafio = DesafioGrupal(
            profesor_id=profesor_id,
            anio_lectivo_id=al.id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            tipo=data.tipo,
            objetivo_cantidad=data.objetivo_cantidad,
            parametro_adicional=data.parametro_adicional,
            recompensa_texto=data.recompensa_texto,
            recompensa_puntos=data.recompensa_puntos,
            fecha_limite=data.fecha_limite
        )

        desafio = await self.repo.create_desafio_grupal(desafio)
        await self.repo.asignar_desafio_a_grupos(desafio.id, equipos)
        await self.db.commit()

        return await self._detalle_desafio(desafio, datetime.utcnow())

    async def get_desafios(self, profesor_id: int) -> List[DesafioGrupalDetalle]:
        """Lista desafíos del profesor con progreso calculado en tiempo real."""
        desafios = await self.repo.get_desafios_profesor(profesor_id)
        ahora = datetime.utcnow()
        return [await self._detalle_desafio(d, ahora) for d in desafios]

    async def eliminar_desafio(self, desafio_id: int, profesor_id: int):
        """Elimina (soft delete) un desafío de un año lectivo activo."""
        desafio = await self.repo.get_desafio_by_id(desafio_id, profesor_id)
        if not desafio:
            raise ValueError("Desafío no encontrado")
        al = await self.school.anio_del_profesor(desafio.anio_lectivo_id, profesor_id)
        if al.estado != ANIO_ACTIVO:
            raise AnioCerrado()

        await self.repo.eliminar_desafio(desafio)
        await self.db.commit()

    # ==================== MONITOREO ====================

    async def get_estadisticas_grupo(self, grupo_id: int, profesor_id: int) -> Optional[EstadisticasGrupo]:
        """Obtiene estadísticas del grupo."""
        try:
            grupo = await self.school.grupo_del_profesor(grupo_id, profesor_id)
        except NoEncontrado:
            return None

        estudiantes_ids = [e.estudiante_id for e in grupo.estudiantes if e.activo]
        if not estudiantes_ids:
            return EstadisticasGrupo(
                grupo_id=grupo.id,
                nombre_grupo=grupo.nombre,
                total_estudiantes=0,
                estudiantes_activos=0,
                estudiantes_inactivos=0,
                promedio_precision=0.0,
                promedio_velocidad=0.0,
                problemas_resueltos_total=0,
                problemas_resueltos_hoy=0,
                distribucion_niveles={},
                estudiantes_rezagados=0,
                estudiantes_estancados=0,
                estudiantes_sobresalientes=0
            )
        
        # Métricas agregadas
        result = await self.db.execute(
            select(
                func.avg(PerfilEstudiante.precision_ultimos_15),
                func.avg(PerfilEstudiante.velocidad_promedio)
            ).where(PerfilEstudiante.estudiante_id.in_(estudiantes_ids))
        )
        promedios = result.first()
        
        # Distribución por nivel
        result = await self.db.execute(
            select(
                PerfilEstudiante.nivel_actual,
                func.count(PerfilEstudiante.estudiante_id)
            )
            .where(PerfilEstudiante.estudiante_id.in_(estudiantes_ids))
            .group_by(PerfilEstudiante.nivel_actual)
        )
        distribucion = {nivel: count for nivel, count in result.all()}
        
        # Activos/inactivos (últimos 7 días)
        hace_7_dias = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(func.count(PerfilEstudiante.estudiante_id))
            .where(and_(
                PerfilEstudiante.estudiante_id.in_(estudiantes_ids),
                PerfilEstudiante.ultima_actividad >= hace_7_dias
            ))
        )
        activos = result.scalar() or 0
        
        # Problemas resueltos total
        result = await self.db.execute(
            select(func.count(Intento.id))
            .where(Intento.estudiante_id.in_(estudiantes_ids))
        )
        total_problemas = result.scalar() or 0
        
        problemas_hoy = await self.repo.get_problemas_resueltos_hoy(estudiantes_ids)
        
        # Alertas (rezagados, estancados, sobresalientes)
        result = await self.db.execute(
            select(func.count(PerfilEstudiante.estudiante_id))
            .where(and_(
                PerfilEstudiante.estudiante_id.in_(estudiantes_ids),
                PerfilEstudiante.precision_ultimos_15 < 0.5
            ))
        )
        rezagados = result.scalar() or 0
        
        result = await self.db.execute(
            select(func.count(PerfilEstudiante.estudiante_id))
            .where(and_(
                PerfilEstudiante.estudiante_id.in_(estudiantes_ids),
                PerfilEstudiante.sesiones_en_nivel_actual >= 10
            ))
        )
        estancados = result.scalar() or 0
        
        result = await self.db.execute(
            select(func.count(PerfilEstudiante.estudiante_id))
            .where(and_(
                PerfilEstudiante.estudiante_id.in_(estudiantes_ids),
                PerfilEstudiante.precision_ultimos_15 >= 0.9
            ))
        )
        sobresalientes = result.scalar() or 0
        
        return EstadisticasGrupo(
            grupo_id=grupo.id,
            nombre_grupo=grupo.nombre,
            total_estudiantes=len(estudiantes_ids),
            estudiantes_activos=activos,
            estudiantes_inactivos=len(estudiantes_ids) - activos,
            promedio_precision=round(float(promedios[0] or 0.0) * 100, 2),
            promedio_velocidad=round(float(promedios[1] or 0.0), 2),
            problemas_resueltos_total=total_problemas,
            problemas_resueltos_hoy=problemas_hoy,
            distribucion_niveles=distribucion,
            estudiantes_rezagados=rezagados,
            estudiantes_estancados=estancados,
            estudiantes_sobresalientes=sobresalientes
        )
    
    async def get_alertas(self, profesor_id: int) -> List[AlertaEstudianteResponse]:
        """Genera alertas en tiempo real basadas en métricas de PerfilEstudiante.

        Reglas con período de gracia (mínimo 3 sesiones antes de alertar):
        - REZAGADO: precisión < 50% con ≥ 3 sesiones
        - INACTIVO: sin actividad > 7 días con ≥ 3 sesiones
        - DIFICULTAD_PERSISTENTE: ≥ 10 sesiones en mismo nivel
        - EXCELENCIA: precisión ≥ 90% con ≥ 5 sesiones
        - PROMOCION_RAPIDA: ≥ 2 subidas de nivel en las últimas 3 sesiones completadas
        - POSIBLE_TRAMPA: alertas guardadas al completar cada práctica (ver PracticeService)
        """
        # Estudiantes de los salones activos del profesor
        estudiantes_ids = list(set(await self.school.ids_estudiantes_del_profesor(profesor_id)))

        if not estudiantes_ids:
            return []

        # Perfiles y datos de estudiante en una sola query
        result = await self.db.execute(
            select(Estudiante, PerfilEstudiante)
            .join(PerfilEstudiante, Estudiante.id == PerfilEstudiante.estudiante_id)
            .where(Estudiante.id.in_(estudiantes_ids))
        )
        rows = result.all()

        alertas: List[AlertaEstudianteResponse] = []
        ahora = datetime.utcnow()
        hace_7_dias = ahora - timedelta(days=7)
        id_contador = 1

        for estudiante, perfil in rows:
            total_sesiones = perfil.total_sesiones or 0

            # ── Período de gracia: estudiantes muy nuevos no generan alertas ──
            if total_sesiones < 3 or perfil.ultima_actividad is None:
                continue

            precision = float(perfil.precision_ultimos_15 or 0.0)
            sesiones_en_nivel = perfil.sesiones_en_nivel_actual or 0
            ultima = perfil.ultima_actividad

            # ── REZAGADO: precisión baja con suficiente historial ─────────────
            if precision < 0.5:
                alertas.append(AlertaEstudianteResponse(
                    id=id_contador,
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_estudiante=estudiante.nombre_completo,
                    tipo=TipoAlerta.REZAGADO,
                    severidad="alta",
                    titulo="Estudiante rezagado",
                    mensaje=(
                        f"Precisión actual: {round(precision * 100)}% en las últimas 15 respuestas. "
                        f"Podría necesitar apoyo adicional."
                    ),
                    datos_contexto={
                        "precision_pct": round(precision * 100, 1),
                        "total_sesiones": total_sesiones,
                    },
                    activa=True,
                    leida=False,
                    fecha_creacion=ahora,
                ))
                id_contador += 1

            # ── INACTIVO: sin práctica en más de 7 días ───────────────────────
            if ultima < hace_7_dias:
                dias = (ahora - ultima).days
                alertas.append(AlertaEstudianteResponse(
                    id=id_contador,
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_estudiante=estudiante.nombre_completo,
                    tipo=TipoAlerta.INACTIVO,
                    severidad="media",
                    titulo="Estudiante inactivo",
                    mensaje=(
                        f"Sin actividad desde hace {dias} días. "
                        f"Última sesión: {ultima.strftime('%d/%m/%Y')}."
                    ),
                    datos_contexto={"dias_sin_actividad": dias},
                    activa=True,
                    leida=False,
                    fecha_creacion=ahora,
                ))
                id_contador += 1

            # ── DIFICULTAD_PERSISTENTE: muchas sesiones sin avanzar nivel ──────
            if sesiones_en_nivel >= 10:
                alertas.append(AlertaEstudianteResponse(
                    id=id_contador,
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_estudiante=estudiante.nombre_completo,
                    tipo=TipoAlerta.DIFICULTAD_PERSISTENTE,
                    severidad="media",
                    titulo="Dificultad persistente en nivel",
                    mensaje=(
                        f"Lleva {sesiones_en_nivel} sesiones en nivel {perfil.nivel_actual} "
                        f"sin avanzar al siguiente nivel."
                    ),
                    datos_contexto={
                        "nivel": perfil.nivel_actual,
                        "sesiones_en_nivel": sesiones_en_nivel,
                    },
                    activa=True,
                    leida=False,
                    fecha_creacion=ahora,
                ))
                id_contador += 1

            # ── EXCELENCIA: rendimiento sobresaliente con historial suficiente ─
            if precision >= 0.9 and total_sesiones >= 5:
                alertas.append(AlertaEstudianteResponse(
                    id=id_contador,
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_estudiante=estudiante.nombre_completo,
                    tipo=TipoAlerta.EXCELENCIA,
                    severidad="baja",
                    titulo="Rendimiento sobresaliente",
                    mensaje=(
                        f"Precisión del {round(precision * 100)}% en las últimas 15 respuestas. "
                        f"¡Excelente desempeño!"
                    ),
                    datos_contexto={
                        "precision_pct": round(precision * 100, 1),
                        "total_sesiones": total_sesiones,
                    },
                    activa=True,
                    leida=False,
                    fecha_creacion=ahora,
                ))
                id_contador += 1

        # ── PROMOCION_RAPIDA: 2 o más subidas de nivel en las últimas 3 sesiones ─
        sesiones_res = await self.db.execute(
            select(SesionPractica.estudiante_id, SesionPractica.cambios_nivel)
            .where(and_(
                SesionPractica.estudiante_id.in_(estudiantes_ids),
                SesionPractica.estado == EstadoSesion.COMPLETADA,
            ))
            .order_by(SesionPractica.estudiante_id, SesionPractica.fecha_fin.desc())
        )
        ultimas: dict = {}
        for est_id, cambios in sesiones_res.all():
            lista = ultimas.setdefault(est_id, [])
            if len(lista) < 3:
                lista.append(cambios or {})
        for estudiante, _perfil in rows:
            subidas = sum(
                1
                for cambios in ultimas.get(estudiante.id, [])
                for c in cambios.values()
                if isinstance(c, dict) and c.get("despues", 0) > c.get("antes", 0)
            )
            if subidas >= 2:
                alertas.append(AlertaEstudianteResponse(
                    id=id_contador,
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_estudiante=estudiante.nombre_completo,
                    tipo=TipoAlerta.PROMOCION_RAPIDA,
                    severidad="baja",
                    titulo="Avance rápido",
                    mensaje=(
                        f"Subió de nivel {subidas} veces en sus últimas 3 sesiones. "
                        f"Podría necesitar retos más exigentes."
                    ),
                    datos_contexto={"subidas_ultimas_3_sesiones": subidas},
                    activa=True,
                    leida=False,
                    fecha_creacion=ahora,
                ))
                id_contador += 1

        # ── POSIBLE_TRAMPA: alertas persistidas al completar cada práctica ─────
        # (velocidad sospechosa, patrón perfecto, outlier del grupo). A diferencia
        # de las anteriores, se calculan en el momento de la sesión y se guardan.
        severidad_profesor = {"critical": "alta", "warning": "media"}
        estudiantes_por_id = {est.id: est for est, _ in rows}
        trampas = await self.db.execute(
            select(AlertaEstudiante)
            .where(and_(
                AlertaEstudiante.estudiante_id.in_(estudiantes_ids),
                AlertaEstudiante.tipo == TipoAlerta.POSIBLE_TRAMPA,
                AlertaEstudiante.activa == True,
            ))
            .order_by(AlertaEstudiante.fecha_creacion.desc())
        )
        for alerta in trampas.scalars().all():
            estudiante = estudiantes_por_id.get(alerta.estudiante_id)
            if estudiante is None:
                continue
            alertas.append(AlertaEstudianteResponse(
                id=1_000_000 + alerta.id,
                estudiante_id=estudiante.id,
                codigo_estudiante=estudiante.codigo_estudiante,
                nombre_estudiante=estudiante.nombre_completo,
                tipo=TipoAlerta.POSIBLE_TRAMPA,
                severidad=severidad_profesor.get(alerta.severidad, alerta.severidad),
                titulo=alerta.titulo,
                mensaje=alerta.mensaje,
                datos_contexto=alerta.datos_contexto,
                activa=alerta.activa,
                leida=alerta.leida,
                fecha_creacion=alerta.fecha_creacion,
            ))

        return alertas
