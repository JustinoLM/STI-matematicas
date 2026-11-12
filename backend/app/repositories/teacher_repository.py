"""Repositorio para operaciones de profesor."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.practice_config import ConfiguracionPractica
from app.models.problem import Intento


class TeacherRepository:
    """Repositorio para operaciones del profesor."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Los grupos, salones y matrículas viven en app.services.school_service.

    # ==================== CONFIGURACIÓN ====================
    
    async def create_configuracion(self, config: ConfiguracionPractica) -> ConfiguracionPractica:
        """Crea la configuración del año lectivo y desactiva las anteriores."""
        result = await self.db.execute(
            select(ConfiguracionPractica)
            .where(ConfiguracionPractica.anio_lectivo_id == config.anio_lectivo_id)
        )
        for anterior in result.scalars().all():
            anterior.activa = False

        self.db.add(config)
        await self.db.flush()
        return config

    async def get_configuracion_activa(self, anio_lectivo_id: int) -> Optional[ConfiguracionPractica]:
        """Configuración activa más reciente del año lectivo."""
        result = await self.db.execute(
            select(ConfiguracionPractica)
            .where(and_(
                ConfiguracionPractica.anio_lectivo_id == anio_lectivo_id,
                ConfiguracionPractica.activa == True  # noqa: E712
            ))
            .order_by(ConfiguracionPractica.fecha_aplicacion.desc(), ConfiguracionPractica.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ==================== DESAFÍOS ====================
    
    async def create_desafio_grupal(self, desafio: DesafioGrupal) -> DesafioGrupal:
        """Crea desafío grupal."""
        self.db.add(desafio)
        await self.db.flush()
        return desafio
    
    async def asignar_desafio_a_grupos(self, desafio_id: int, grupos_ids: List[Optional[int]]):
        """Crea los equipos del desafío (grupo_id None = el salón completo)."""
        for grupo_id in grupos_ids:
            relacion = GrupoDesafio(
                desafio_id=desafio_id,
                grupo_id=grupo_id,
                progreso_actual=0
            )
            self.db.add(relacion)
        await self.db.flush()
    
    async def get_desafios_profesor(self, profesor_id: int, incluir_eliminados: bool = False) -> List[DesafioGrupal]:
        """Obtiene desafíos del profesor."""
        query = select(DesafioGrupal).where(DesafioGrupal.profesor_id == profesor_id)
        
        if not incluir_eliminados:
            query = query.where(DesafioGrupal.eliminado == False)
        
        result = await self.db.execute(
            query.options(selectinload(DesafioGrupal.grupos))
        )
        return list(result.scalars().all())
    
    async def get_desafio_by_id(self, desafio_id: int, profesor_id: int) -> Optional[DesafioGrupal]:
        """Obtiene desafío por ID."""
        result = await self.db.execute(
            select(DesafioGrupal)
            .where(and_(
                DesafioGrupal.id == desafio_id,
                DesafioGrupal.profesor_id == profesor_id
            ))
            .options(selectinload(DesafioGrupal.grupos))
        )
        return result.scalar_one_or_none()
    
    async def eliminar_desafio(self, desafio: DesafioGrupal):
        """Elimina (soft delete) desafío."""
        desafio.eliminado = True
        await self.db.flush()
    
    # ==================== ALERTAS ====================
    
    # ==================== ESTADÍSTICAS ====================
    
    async def get_problemas_resueltos_hoy(self, estudiantes_ids: List[int]) -> int:
        """Cuenta problemas resueltos hoy por estudiantes."""
        hoy = datetime.utcnow().date()
        result = await self.db.execute(
            select(func.count(Intento.id))
            .where(and_(
                Intento.estudiante_id.in_(estudiantes_ids),
                func.date(Intento.timestamp) == hoy
            ))
        )
        return result.scalar() or 0
