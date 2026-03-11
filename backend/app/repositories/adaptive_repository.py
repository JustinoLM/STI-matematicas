"""
Repository para operaciones de base de datos del sistema adaptativo.

Gestiona perfiles, diagnósticos, sesiones y alertas.
"""

from typing import Optional, List, Dict
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.adaptive import (
    PerfilEstudiante,
    PruebaDiagnostica,
    SesionPractica,
    EstadoSesion,
    AlertaEstudiante,
    EstadoDiagnostico,
    TipoAlerta,
    PerfilAprendizaje
)
from app.models.problem import Intento, Problema


class AdaptiveRepository:
    """Repository para operaciones del sistema adaptativo."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================
    # Operaciones de Perfil
    # ============================================
    
    async def get_perfil(self, estudiante_id: int) -> Optional[PerfilEstudiante]:
        """Obtiene el perfil de un estudiante."""
        result = await self.db.execute(
            select(PerfilEstudiante).where(PerfilEstudiante.estudiante_id == estudiante_id)
        )
        return result.scalar_one_or_none()
    
    async def create_perfil(self, estudiante_id: int) -> PerfilEstudiante:
        """Crea un perfil nuevo con valores por defecto."""
        perfil = PerfilEstudiante(
            estudiante_id=estudiante_id,
            nivel_suma=1,
            nivel_resta=1,
            nivel_multiplicacion=1,
            nivel_division=1,
            nivel_actual=1
        )
        
        self.db.add(perfil)
        await self.db.commit()
        await self.db.refresh(perfil)
        
        return perfil
    
    async def update_perfil(self, perfil: PerfilEstudiante) -> PerfilEstudiante:
        """Actualiza un perfil existente."""
        perfil.fecha_actualizacion = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(perfil)
        return perfil
    
    async def get_or_create_perfil(self, estudiante_id: int) -> PerfilEstudiante:
        """Obtiene perfil o lo crea si no existe."""
        perfil = await self.get_perfil(estudiante_id)
        if not perfil:
            perfil = await self.create_perfil(estudiante_id)
        return perfil
    
    # ============================================
    # Operaciones de Diagnóstico
    # ============================================
    
    async def create_diagnostico(self, estudiante_id: int, problemas_ids: List[int]) -> PruebaDiagnostica:
        """Crea una prueba diagnóstica."""
        diagnostico = PruebaDiagnostica(
            estudiante_id=estudiante_id,
            estado=EstadoDiagnostico.EN_PROGRESO,
            fecha_inicio=datetime.utcnow(),
            problemas_ids=problemas_ids
        )
        
        self.db.add(diagnostico)
        await self.db.commit()
        await self.db.refresh(diagnostico)
        
        return diagnostico
    
    async def get_diagnostico(self, diagnostico_id: int) -> Optional[PruebaDiagnostica]:
        """Obtiene un diagnóstico por ID."""
        result = await self.db.execute(
            select(PruebaDiagnostica).where(PruebaDiagnostica.id == diagnostico_id)
        )
        return result.scalar_one_or_none()
    
    async def get_diagnostico_by_estudiante(self, estudiante_id: int) -> Optional[PruebaDiagnostica]:
        """Obtiene el diagnóstico de un estudiante."""
        result = await self.db.execute(
            select(PruebaDiagnostica)
            .where(PruebaDiagnostica.estudiante_id == estudiante_id)
            .order_by(PruebaDiagnostica.fecha_inicio.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def update_diagnostico(self, diagnostico: PruebaDiagnostica) -> PruebaDiagnostica:
        """Actualiza un diagnóstico."""
        await self.db.commit()
        await self.db.refresh(diagnostico)
        return diagnostico
    
    # ============================================
    # Operaciones de Sesión
    # ============================================
    
    async def create_sesion(
        self,
        estudiante_id: int,
        perfil: PerfilEstudiante,
        cantidad_problemas: int,
        problemas_ids: List[int],
        operaciones_incluidas: Dict[str, int],
        ratio_dificultad: Dict[str, float]
    ) -> SesionPractica:
        """Crea una nueva sesión de práctica."""
        sesion = SesionPractica(
            estudiante_id=estudiante_id,
            perfil_id=perfil.estudiante_id,
            nivel_actual_inicio=perfil.nivel_actual,
            nivel_suma_inicio=perfil.nivel_suma,
            nivel_resta_inicio=perfil.nivel_resta,
            nivel_multiplicacion_inicio=perfil.nivel_multiplicacion,
            nivel_division_inicio=perfil.nivel_division,
            cantidad_problemas=cantidad_problemas,
            problemas_ids=problemas_ids,
            operaciones_incluidas=operaciones_incluidas,
            ratio_dificultad=ratio_dificultad
        )
        
        self.db.add(sesion)
        await self.db.commit()
        await self.db.refresh(sesion)
        
        return sesion
    
    async def get_sesion(self, sesion_id: int) -> Optional[SesionPractica]:
        """Obtiene una sesión por ID."""
        result = await self.db.execute(
            select(SesionPractica).where(SesionPractica.id == sesion_id)
        )
        return result.scalar_one_or_none()

    async def get_sesion_activa(self, estudiante_id: int) -> Optional[SesionPractica]:
        """
        Devuelve la sesión EN_PROGRESO más reciente del estudiante
        siempre que tenga menos de 90 minutos de inactividad.
        """
        limite = datetime.utcnow() - timedelta(minutes=90)
        result = await self.db.execute(
            select(SesionPractica)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.EN_PROGRESO,
                    SesionPractica.fecha_ultima_actividad >= limite,
                )
            )
            .order_by(SesionPractica.fecha_ultima_actividad.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def update_sesion(self, sesion: SesionPractica) -> SesionPractica:
        """Actualiza una sesión."""
        await self.db.commit()
        await self.db.refresh(sesion)
        return sesion
    
    async def get_ultimas_sesiones(
        self,
        estudiante_id: int,
        limit: int = 10
    ) -> List[SesionPractica]:
        """Obtiene las últimas N sesiones de un estudiante."""
        result = await self.db.execute(
            select(SesionPractica)
            .where(SesionPractica.estudiante_id == estudiante_id)
            .order_by(SesionPractica.fecha_inicio.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ============================================
    # Operaciones de Intentos (extendidas)
    # ============================================
    
    async def get_intentos_sesion(self, sesion_id: int) -> List[Intento]:
        """Obtiene todos los intentos de una sesión."""
        result = await self.db.execute(
            select(Intento)
            .where(Intento.sesion_id == sesion_id)
            .order_by(Intento.timestamp.asc())
        )
        return list(result.scalars().all())
    
    async def get_ultimos_intentos(
        self,
        estudiante_id: int,
        limit: int = 15
    ) -> List[Intento]:
        """Obtiene los últimos N intentos de un estudiante."""
        result = await self.db.execute(
            select(Intento)
            .where(Intento.estudiante_id == estudiante_id)
            .order_by(Intento.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ============================================
    # Redención
    # ============================================

    async def get_problemas_fallados(
        self,
        estudiante_id: int,
        limit: int = 50
    ) -> List[int]:
        """
        Retorna IDs de problemas que el estudiante NUNCA resolvió correctamente.

        Condición: tiene al menos un intento pero ninguno fue correcto.
        Usado para construir sesiones de Redención (máx. 5 problemas al azar).
        """
        from sqlalchemy import not_

        # Sub-consulta: problema_ids con al menos un intento correcto
        correctos_subq = (
            select(Intento.problema_id)
            .where(
                and_(
                    Intento.estudiante_id == estudiante_id,
                    Intento.es_correcto == True  # noqa: E712
                )
            )
            .distinct()
            .scalar_subquery()
        )

        result = await self.db.execute(
            select(Intento.problema_id)
            .where(
                and_(
                    Intento.estudiante_id == estudiante_id,
                    not_(Intento.problema_id.in_(correctos_subq))
                )
            )
            .distinct()
            .limit(limit)
        )
        return [row[0] for row in result.all()]

    # ============================================
    # Estadísticas de Grupo
    # ============================================

    async def get_velocidades_grupo(self, grupo_id: int) -> List[float]:
        """Obtiene velocidades promedio de todos los estudiantes del grupo."""
        # TODO: Implementar cuando tengamos la relación estudiante-grupo
        # Por ahora retorna lista vacía
        return []
    
    async def get_precisiones_grupo(self, grupo_id: int) -> List[float]:
        """Obtiene precisiones de todos los estudiantes del grupo."""
        # TODO: Implementar cuando tengamos la relación estudiante-grupo
        return []
    
    # ============================================
    # Operaciones de Alertas (preparado para futuro)
    # ============================================
    
    async def create_alerta(
        self,
        estudiante_id: int,
        tipo: TipoAlerta,
        titulo: str,
        mensaje: str,
        severidad: str = "info",
        datos_contexto: Optional[Dict] = None
    ) -> AlertaEstudiante:
        """Crea una nueva alerta."""
        alerta = AlertaEstudiante(
            estudiante_id=estudiante_id,
            perfil_id=estudiante_id,
            tipo=tipo,
            severidad=severidad,
            titulo=titulo,
            mensaje=mensaje,
            datos_contexto=datos_contexto
        )
        
        self.db.add(alerta)
        await self.db.commit()
        await self.db.refresh(alerta)
        
        return alerta
    
    async def get_alertas_activas(self, estudiante_id: int) -> List[AlertaEstudiante]:
        """Obtiene alertas activas de un estudiante."""
        result = await self.db.execute(
            select(AlertaEstudiante)
            .where(
                and_(
                    AlertaEstudiante.estudiante_id == estudiante_id,
                    AlertaEstudiante.activa == True
                )
            )
            .order_by(AlertaEstudiante.fecha_creacion.desc())
        )
        return list(result.scalars().all())
    
    async def count_sesiones_en_rango(
        self,
        estudiante_id: int,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> int:
        """Cuenta sesiones en un rango de fechas."""
        from sqlalchemy import func, and_
        
        result = await self.db.execute(
            select(func.count(SesionPractica.id))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.fecha_inicio >= fecha_inicio,
                    SesionPractica.fecha_inicio < fecha_fin,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
        )
        return result.scalar() or 0
    
    async def get_total_problemas_resueltos(self, estudiante_id: int) -> int:
        """Total de problemas resueltos (todas las sesiones completadas)."""
        from sqlalchemy import func, and_

        result = await self.db.execute(
            select(func.sum(SesionPractica.cantidad_problemas))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
        )
        return result.scalar() or 0

    async def get_mejor_racha_perfectas(self, estudiante_id: int) -> int:
        """Mejor racha histórica de sesiones perfectas (100% de aciertos) del estudiante."""
        result = await self.db.execute(
            select(SesionPractica.es_practica_perfecta)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
            .order_by(SesionPractica.fecha_inicio.asc())
        )
        sesiones = result.scalars().all()

        racha_actual = 0
        mejor_racha = 0
        for es_perfecta in sesiones:
            if es_perfecta:
                racha_actual += 1
                mejor_racha = max(mejor_racha, racha_actual)
            else:
                racha_actual = 0
        return mejor_racha
    
    async def get_grupo_info(self, estudiante_id: int) -> Optional[dict]:
        """Obtiene el nombre del grupo y del profesor asignado al estudiante."""
        from app.models.group import EstudianteGrupo, Grupo
        from app.models.user import Profesor

        result = await self.db.execute(
            select(Grupo.nombre, Profesor.nombre_completo)
            .join(EstudianteGrupo, EstudianteGrupo.grupo_id == Grupo.id)
            .join(Profesor, Grupo.profesor_id == Profesor.id)
            .where(
                and_(
                    EstudianteGrupo.estudiante_id == estudiante_id,
                    EstudianteGrupo.activo == True,
                    Grupo.activo == True,
                )
            )
            .limit(1)
        )
        row = result.first()
        if row:
            return {"grupo_nombre": row[0], "profesor_nombre": row[1]}
        return None

    async def get_config_practica_estudiante(self, estudiante_id: int):
        """Obtiene la ConfiguracionPractica activa del grupo del estudiante, o None."""
        from app.models.group import EstudianteGrupo, Grupo
        from app.models.practice_config import ConfiguracionPractica

        # Primero obtener el grupo_id activo del estudiante
        grupo_result = await self.db.execute(
            select(Grupo.id)
            .join(EstudianteGrupo, EstudianteGrupo.grupo_id == Grupo.id)
            .where(
                and_(
                    EstudianteGrupo.estudiante_id == estudiante_id,
                    EstudianteGrupo.activo == True,
                    Grupo.activo == True,
                )
            )
            .limit(1)
        )
        grupo_row = grupo_result.first()
        if not grupo_row:
            return None

        grupo_id = grupo_row[0]

        # Obtener la config activa más reciente
        config_result = await self.db.execute(
            select(ConfiguracionPractica)
            .where(
                and_(
                    ConfiguracionPractica.grupo_id == grupo_id,
                    ConfiguracionPractica.activa == True,
                )
            )
            .order_by(ConfiguracionPractica.fecha_aplicacion.desc())
            .limit(1)
        )
        return config_result.scalar_one_or_none()

    async def get_problema(self, problema_id: int) -> Optional[Problema]:
        """Obtiene un problema por ID."""
        result = await self.db.execute(
            select(Problema).where(Problema.id == problema_id)
        )
        return result.scalar_one_or_none()
    
    async def update_problema(self, problema: Problema) -> Problema:
        """Actualiza un problema."""
        await self.db.commit()
        await self.db.refresh(problema)
        return problema
    
    async def get_intentos_problema(
        self,
        estudiante_id: int,
        problema_id: int
    ) -> List[Intento]:
        """Obtiene todos los intentos de un estudiante en un problema."""
        result = await self.db.execute(
            select(Intento)
            .where(
                and_(
                    Intento.estudiante_id == estudiante_id,
                    Intento.problema_id == problema_id
                )
            )
            .order_by(Intento.timestamp)
        )
        return list(result.scalars().all())
