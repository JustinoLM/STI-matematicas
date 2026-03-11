"""Service para operaciones del profesor."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.teacher_repository import TeacherRepository
from app.models.user import Estudiante
from app.models.group import EstudianteGrupo
from app.models.adaptive import PerfilEstudiante, AlertaEstudiante, TipoAlerta, SesionPractica, EstadoSesion
from app.models.practice_config import ConfiguracionPractica
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.problem import Intento
from app.schemas.teacher import (
    GrupoCreate, GrupoUpdate, GrupoDetalle, GrupoResumen, EstudianteEnGrupo,
    ConfiguracionPracticaCreate, ConfiguracionPracticaResponse,
    DesafioGrupalCreate, DesafioGrupalDetalle, DesafioGrupalResumen, ProgresoGrupoDesafio,
    EstadisticasGrupo, ProgresoEstudiante, AlertaEstudianteResponse
)


class TeacherService:
    """Service para APIs del profesor."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TeacherRepository(db)
    
    # ==================== GRUPOS ====================
    
    async def crear_grupo(self, profesor_id: int, data: GrupoCreate) -> GrupoDetalle:
        """Crea un grupo."""
        grupo = await self.repo.create_grupo(
            profesor_id=profesor_id,
            nombre=data.nombre,
            codigo_grupo=data.codigo_grupo
        )
        await self.db.commit()
        
        return GrupoDetalle(
            id=grupo.id,
            nombre=grupo.nombre,
            codigo_grupo=grupo.codigo_grupo,
            activo=grupo.activo,
            profesor_id=grupo.profesor_id,
            cantidad_estudiantes=0,
            estudiantes=[]
        )
    
    async def get_grupos(self, profesor_id: int) -> List[GrupoResumen]:
        """Lista grupos del profesor con resumen."""
        grupos = await self.repo.get_grupos_profesor(profesor_id)
        
        resumenes = []
        for grupo in grupos:
            estudiantes_ids = [e.estudiante_id for e in grupo.estudiantes if e.activo]
            
            # Calcular promedio precisión
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
                codigo_grupo=grupo.codigo_grupo,
                activo=grupo.activo,
                cantidad_estudiantes=len(estudiantes_ids),
                promedio_precision=round(promedio * 100, 2),
                problemas_resueltos_hoy=problemas_hoy
            ))
        
        return resumenes
    
    async def get_grupo_detalle(self, grupo_id: int, profesor_id: int) -> Optional[GrupoDetalle]:
        """Obtiene detalle de grupo con estudiantes."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
            return None
        
        estudiantes_lista = []
        for rel in grupo.estudiantes:
            if not rel.activo:
                continue
            
            # Obtener estudiante y perfil
            result = await self.db.execute(
                select(Estudiante, PerfilEstudiante)
                .join(PerfilEstudiante, Estudiante.id == PerfilEstudiante.estudiante_id)
                .where(Estudiante.id == rel.estudiante_id)
            )
            row = result.first()
            
            if row:
                estudiante, perfil = row
                estudiantes_lista.append(EstudianteEnGrupo(
                    estudiante_id=estudiante.id,
                    codigo_estudiante=estudiante.codigo_estudiante,
                    nombre_completo=estudiante.nombre_completo,
                    nivel_actual=perfil.nivel_actual,
                    precision_ultimos_15=float(perfil.precision_ultimos_15 or 0.0) * 100,
                    fecha_ingreso=rel.fecha_ingreso,
                    activo=rel.activo
                ))
        
        return GrupoDetalle(
            id=grupo.id,
            nombre=grupo.nombre,
            codigo_grupo=grupo.codigo_grupo,
            activo=grupo.activo,
            profesor_id=grupo.profesor_id,
            cantidad_estudiantes=len(estudiantes_lista),
            estudiantes=estudiantes_lista
        )
    
    async def agregar_estudiante(self, grupo_id: int, estudiante_id: int, profesor_id: int):
        """Agrega estudiante a grupo. Crea PerfilEstudiante si no tiene."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
            raise ValueError("Grupo no encontrado")

        await self.repo.agregar_estudiante_a_grupo(grupo_id, estudiante_id)
        await self.repo.ensure_perfil_estudiante(estudiante_id)
        await self.db.commit()
    
    async def remover_estudiante(self, grupo_id: int, estudiante_id: int, profesor_id: int):
        """Remueve estudiante de grupo."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
            raise ValueError("Grupo no encontrado")

        await self.repo.remover_estudiante_de_grupo(grupo_id, estudiante_id)
        await self.db.commit()

    async def eliminar_grupo(self, grupo_id: int, profesor_id: int):
        """Elimina un grupo. Solo el profesor dueño puede eliminarlo."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
            raise ValueError("Grupo no encontrado o no tienes permiso para eliminarlo")
        await self.repo.eliminar_grupo(grupo)
        await self.db.commit()

    # ==================== CONFIGURACIÓN ====================
    
    async def crear_configuracion(
        self, 
        profesor_id: int, 
        data: ConfiguracionPracticaCreate
    ) -> ConfiguracionPracticaResponse:
        """Crea configuración de práctica."""
        grupo = await self.repo.get_grupo_by_id(data.grupo_id, profesor_id)
        if not grupo:
            raise ValueError("Grupo no encontrado")
        
        config = ConfiguracionPractica(
            grupo_id=data.grupo_id,
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
    
    async def get_configuracion_activa(self, grupo_id: int, profesor_id: int) -> Optional[ConfiguracionPracticaResponse]:
        """Obtiene configuración activa."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
            return None
        
        config = await self.repo.get_configuracion_activa(grupo_id)
        if not config:
            return None
        
        return ConfiguracionPracticaResponse.model_validate(config)
    
    # ==================== DESAFÍOS ====================

    async def _calcular_progreso_desafio(
        self, desafio: DesafioGrupal, grupo_id: int
    ) -> int:
        """Calcula el progreso real de un desafío para un grupo desde SesionPractica.

        Ventana de tiempo: [fecha_creacion, fecha_limite] (si fecha_limite existe).

        Tipos soportados (de más fácil a más difícil):
        - problemas_resueltos    → SUM(problemas_correctos)
        - sesiones_completadas   → COUNT(sesiones)
        - practicas_sin_errores  → COUNT(sesiones donde incorrectos <= parametro_adicional)
        - problemas_rapidos      → SUM(correctos) de sesiones donde velocidad_promedio <= parametro_adicional seg
        - practicas_rapidas      → COUNT(sesiones donde tiempo_total <= parametro_adicional * 60 seg)
        """
        # Estudiantes activos en el grupo
        result = await self.db.execute(
            select(EstudianteGrupo.estudiante_id)
            .where(and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.activo == True,
            ))
        )
        estudiantes_ids = [row[0] for row in result.all()]

        if not estudiantes_ids:
            return 0

        # Condiciones base: ventana de tiempo del desafío
        condiciones = [
            SesionPractica.estudiante_id.in_(estudiantes_ids),
            SesionPractica.estado == EstadoSesion.COMPLETADA,
            SesionPractica.fecha_fin >= desafio.fecha_creacion,
        ]
        # Si tiene fecha límite, solo cuentan sesiones ANTES del vencimiento
        if desafio.fecha_limite:
            condiciones.append(SesionPractica.fecha_fin <= desafio.fecha_limite)

        base_where = and_(*condiciones)

        # ── 1. Resolver X problemas ──────────────────────────────────────────
        if desafio.tipo == "problemas_resueltos":
            result = await self.db.execute(
                select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0))
                .where(and_(base_where, SesionPractica.problemas_correctos.isnot(None)))
            )
            return int(result.scalar() or 0)

        # ── 2. Resolver X prácticas ──────────────────────────────────────────
        elif desafio.tipo == "sesiones_completadas":
            result = await self.db.execute(
                select(func.count(SesionPractica.id)).where(base_where)
            )
            return int(result.scalar() or 0)

        # ── 3. Resolver X prácticas con máximo Y errores ─────────────────────
        elif desafio.tipo == "practicas_sin_errores":
            max_errores = desafio.parametro_adicional or 0
            result = await self.db.execute(
                select(func.count(SesionPractica.id))
                .where(and_(
                    base_where,
                    SesionPractica.problemas_incorrectos.isnot(None),
                    SesionPractica.problemas_incorrectos <= max_errores,
                ))
            )
            return int(result.scalar() or 0)

        # ── 4. Resolver X problemas en Y o menos segundos/problema ───────────
        elif desafio.tipo == "problemas_rapidos":
            max_seg = desafio.parametro_adicional or 999
            result = await self.db.execute(
                select(func.coalesce(func.sum(SesionPractica.problemas_correctos), 0))
                .where(and_(
                    base_where,
                    SesionPractica.velocidad_promedio.isnot(None),
                    SesionPractica.velocidad_promedio <= max_seg,
                    SesionPractica.problemas_correctos.isnot(None),
                ))
            )
            return int(result.scalar() or 0)

        # ── 5. Resolver X prácticas en Y o menos minutos ─────────────────────
        elif desafio.tipo == "practicas_rapidas":
            max_min = desafio.parametro_adicional or 999
            max_seg_total = max_min * 60
            result = await self.db.execute(
                select(func.count(SesionPractica.id))
                .where(and_(
                    base_where,
                    SesionPractica.tiempo_total_segundos.isnot(None),
                    SesionPractica.tiempo_total_segundos <= max_seg_total,
                ))
            )
            return int(result.scalar() or 0)

        # Tipo desconocido: devolver 0
        return 0

    async def crear_desafio_grupal(
        self, 
        profesor_id: int, 
        data: DesafioGrupalCreate
    ) -> DesafioGrupalDetalle:
        """Crea desafío grupal."""
        desafio = DesafioGrupal(
            profesor_id=profesor_id,
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
        await self.repo.asignar_desafio_a_grupos(desafio.id, data.grupos_ids)
        await self.db.commit()
        
        # Obtener progreso de grupos
        result = await self.db.execute(
            select(GrupoDesafio)
            .where(GrupoDesafio.desafio_id == desafio.id)
        )
        relaciones = result.scalars().all()
        
        progreso_grupos = []
        for rel in relaciones:
            grupo = await self.repo.get_grupo_by_id(rel.grupo_id, profesor_id)
            if grupo:
                progreso_real = await self._calcular_progreso_desafio(desafio, rel.grupo_id)
                progreso_grupos.append(ProgresoGrupoDesafio(
                    grupo_id=grupo.id,
                    nombre_grupo=grupo.nombre,
                    progreso_actual=progreso_real,
                    objetivo_cantidad=desafio.objetivo_cantidad,
                    porcentaje=min(round((progreso_real / desafio.objetivo_cantidad) * 100, 1), 100.0),
                    completado=progreso_real >= desafio.objetivo_cantidad,
                ))

        return DesafioGrupalDetalle(
            id=desafio.id,
            profesor_id=desafio.profesor_id,
            nombre=desafio.nombre,
            descripcion=desafio.descripcion,
            tipo=desafio.tipo,
            objetivo_cantidad=desafio.objetivo_cantidad,
            parametro_adicional=desafio.parametro_adicional,
            recompensa_texto=desafio.recompensa_texto,
            recompensa_puntos=desafio.recompensa_puntos,
            fecha_creacion=desafio.fecha_creacion,
            fecha_limite=desafio.fecha_limite,
            completado=desafio.completado,
            vencido=False,  # Recién creado, nunca vencido
            eliminado=desafio.eliminado,
            progreso_grupos=progreso_grupos,
        )
    
    async def get_desafios(self, profesor_id: int) -> List[DesafioGrupalDetalle]:
        """Lista desafíos del profesor con progreso calculado en tiempo real.

        Estados posibles:
        - completado=True, vencido=False → Todos los grupos alcanzaron el objetivo
        - completado=False, vencido=True → Fecha límite expiró sin completarse
        - completado=False, vencido=False → Activo, aún en curso
        """
        desafios = await self.repo.get_desafios_profesor(profesor_id)
        ahora = datetime.utcnow()

        resultado = []
        for desafio in desafios:
            result = await self.db.execute(
                select(GrupoDesafio)
                .where(GrupoDesafio.desafio_id == desafio.id)
            )
            relaciones = result.scalars().all()

            progreso_grupos = []
            todos_completados = len(relaciones) > 0  # True hasta que alguno falle

            for rel in relaciones:
                grupo = await self.repo.get_grupo_by_id(rel.grupo_id, profesor_id)
                if grupo:
                    progreso_real = await self._calcular_progreso_desafio(desafio, rel.grupo_id)
                    completado_grupo = progreso_real >= desafio.objetivo_cantidad

                    if not completado_grupo:
                        todos_completados = False

                    porcentaje = min(
                        round((progreso_real / desafio.objetivo_cantidad) * 100, 1),
                        100.0,
                    )
                    progreso_grupos.append(ProgresoGrupoDesafio(
                        grupo_id=grupo.id,
                        nombre_grupo=grupo.nombre,
                        progreso_actual=progreso_real,
                        objetivo_cantidad=desafio.objetivo_cantidad,
                        porcentaje=porcentaje,
                        completado=completado_grupo,
                    ))

            # Un desafío está vencido si su fecha límite pasó y NO fue completado
            vencido = (
                desafio.fecha_limite is not None
                and desafio.fecha_limite < ahora
                and not todos_completados
            )

            resultado.append(DesafioGrupalDetalle(
                id=desafio.id,
                profesor_id=desafio.profesor_id,
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
            ))

        return resultado
    
    async def eliminar_desafio(self, desafio_id: int, profesor_id: int):
        """Elimina desafío."""
        desafio = await self.repo.get_desafio_by_id(desafio_id, profesor_id)
        if not desafio:
            raise ValueError("Desafío no encontrado")
        
        await self.repo.eliminar_desafio(desafio)
        await self.db.commit()
    
    # ==================== MONITOREO ====================
    
    async def get_estadisticas_grupo(self, grupo_id: int, profesor_id: int) -> Optional[EstadisticasGrupo]:
        """Obtiene estadísticas del grupo."""
        grupo = await self.repo.get_grupo_by_id(grupo_id, profesor_id)
        if not grupo:
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
        """
        grupos = await self.repo.get_grupos_profesor(profesor_id)
        grupos_ids = [g.id for g in grupos]

        if not grupos_ids:
            return []

        # IDs únicos de estudiantes activos en los grupos del profesor
        result = await self.db.execute(
            select(EstudianteGrupo.estudiante_id)
            .where(and_(
                EstudianteGrupo.grupo_id.in_(grupos_ids),
                EstudianteGrupo.activo == True
            ))
        )
        estudiantes_ids = list(set(row[0] for row in result.all()))

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

        return alertas
