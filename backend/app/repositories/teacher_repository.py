"""Repositorio para operaciones de profesor."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.adaptive import PerfilEstudiante
from app.models.challenge import DesafioGrupal, GrupoDesafio
from app.models.group import EstudianteGrupo, Grupo
from app.models.practice_config import ConfiguracionPractica
from app.models.problem import Intento


class TeacherRepository:
    """Repositorio para operaciones del profesor."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== GRUPOS ====================
    
    async def get_grupos_profesor(self, profesor_id: int) -> List[Grupo]:
        """Obtiene grupos del profesor."""
        result = await self.db.execute(
            select(Grupo)
            .where(Grupo.profesor_id == profesor_id)
            .options(selectinload(Grupo.estudiantes))
        )
        return list(result.scalars().all())
    
    async def get_grupo_by_id(self, grupo_id: int, profesor_id: int) -> Optional[Grupo]:
        """Obtiene grupo por ID verificando profesor."""
        result = await self.db.execute(
            select(Grupo)
            .where(and_(Grupo.id == grupo_id, Grupo.profesor_id == profesor_id))
            .options(selectinload(Grupo.estudiantes))
        )
        return result.scalar_one_or_none()
    
    async def create_grupo(self, profesor_id: int, nombre: str, codigo_grupo: str) -> Grupo:
        """Crea un grupo."""
        grupo = Grupo(
            profesor_id=profesor_id,
            nombre=nombre,
            codigo_grupo=codigo_grupo
        )
        self.db.add(grupo)
        await self.db.flush()
        return grupo
    
    async def eliminar_grupo(self, grupo: Grupo):
        """Elimina un grupo y todas sus relaciones de estudiantes."""
        # Primero eliminar relaciones estudiante-grupo
        from sqlalchemy import delete as sa_delete
        await self.db.execute(
            sa_delete(EstudianteGrupo).where(EstudianteGrupo.grupo_id == grupo.id)
        )
        await self.db.delete(grupo)
        await self.db.flush()
    
    async def agregar_estudiante_a_grupo(self, grupo_id: int, estudiante_id: int) -> EstudianteGrupo:
        """Agrega estudiante a grupo. Si ya existía (soft-deleted), lo reactiva."""
        result = await self.db.execute(
            select(EstudianteGrupo).where(and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.estudiante_id == estudiante_id
            ))
        )
        relacion = result.scalar_one_or_none()
        if relacion:
            relacion.activo = True
        else:
            relacion = EstudianteGrupo(
                estudiante_id=estudiante_id,
                grupo_id=grupo_id
            )
            self.db.add(relacion)
        await self.db.flush()
        return relacion
    
    async def ensure_perfil_estudiante(self, estudiante_id: int):
        """Crea PerfilEstudiante si el estudiante no tiene uno todavía."""
        result = await self.db.execute(
            select(PerfilEstudiante).where(PerfilEstudiante.estudiante_id == estudiante_id)
        )
        if not result.scalar_one_or_none():
            perfil = PerfilEstudiante(estudiante_id=estudiante_id)
            self.db.add(perfil)
            await self.db.flush()

    async def remover_estudiante_de_grupo(self, grupo_id: int, estudiante_id: int):
        """Remueve estudiante de grupo."""
        await self.db.execute(
            select(EstudianteGrupo)
            .where(and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.estudiante_id == estudiante_id
            ))
        )
        # Soft delete
        result = await self.db.execute(
            select(EstudianteGrupo).where(and_(
                EstudianteGrupo.grupo_id == grupo_id,
                EstudianteGrupo.estudiante_id == estudiante_id
            ))
        )
        relacion = result.scalar_one_or_none()
        if relacion:
            relacion.activo = False
            await self.db.flush()
    
    # ==================== CONFIGURACIÓN ====================
    
    async def create_configuracion(self, config: ConfiguracionPractica) -> ConfiguracionPractica:
        """Crea configuración de práctica."""
        # Desactivar configs anteriores
        await self.db.execute(
            select(ConfiguracionPractica)
            .where(ConfiguracionPractica.grupo_id == config.grupo_id)
        )
        result = await self.db.execute(
            select(ConfiguracionPractica)
            .where(ConfiguracionPractica.grupo_id == config.grupo_id)
        )
        configs_anteriores = result.scalars().all()
        for c in configs_anteriores:
            c.activa = False
        
        self.db.add(config)
        await self.db.flush()
        return config
    
    async def get_configuracion_activa(self, grupo_id: int) -> Optional[ConfiguracionPractica]:
        """Obtiene configuración activa de un grupo."""
        result = await self.db.execute(
            select(ConfiguracionPractica)
            .where(and_(
                ConfiguracionPractica.grupo_id == grupo_id,
                ConfiguracionPractica.activa == True
            ))
            .order_by(ConfiguracionPractica.fecha_aplicacion.desc())
        )
        return result.scalar_one_or_none()
    
    # ==================== DESAFÍOS ====================
    
    async def create_desafio_grupal(self, desafio: DesafioGrupal) -> DesafioGrupal:
        """Crea desafío grupal."""
        self.db.add(desafio)
        await self.db.flush()
        return desafio
    
    async def asignar_desafio_a_grupos(self, desafio_id: int, grupos_ids: List[int]):
        """Asigna desafío a grupos."""
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
