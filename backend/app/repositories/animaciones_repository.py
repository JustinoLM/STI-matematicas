"""
Repositorio para animaciones guardadas (colección paso a paso, máx 10 por estudiante).
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import AnimacionGuardada

MAX_ANIMACIONES = 10


class AnimacionesRepository:
    """Acceso a datos para AnimacionGuardada."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_coleccion(self, estudiante_id: int) -> list[AnimacionGuardada]:
        """Devuelve las animaciones guardadas del estudiante, más recientes primero."""
        result = await self.db.execute(
            select(AnimacionGuardada)
            .where(AnimacionGuardada.estudiante_id == estudiante_id)
            .order_by(AnimacionGuardada.guardado_en.desc())
        )
        return list(result.scalars().all())

    async def get_por_problema(
        self, estudiante_id: int, problema_id: int
    ) -> Optional[AnimacionGuardada]:
        """Comprueba si el estudiante ya guardó esta animación."""
        result = await self.db.execute(
            select(AnimacionGuardada).where(
                AnimacionGuardada.estudiante_id == estudiante_id,
                AnimacionGuardada.problema_id == problema_id,
            )
        )
        return result.scalar_one_or_none()

    async def guardar(
        self,
        estudiante_id: int,
        problema_id: int,
        operacion: str,
        numero1: str,
        numero2: str,
        nivel_dificultad: int,
    ) -> tuple[AnimacionGuardada, Optional[AnimacionGuardada]]:
        """
        Guarda una animación. Si ya existe (mismo problema), devuelve la existente.
        Si hay 10 guardadas, elimina la más antigua antes de guardar.

        Returns:
            (animacion_guardada, animacion_eliminada | None)
        """
        # Si ya está guardada, devolver sin duplicar
        existente = await self.get_por_problema(estudiante_id, problema_id)
        if existente:
            return existente, None

        eliminada: Optional[AnimacionGuardada] = None
        coleccion = await self.get_coleccion(estudiante_id)
        if len(coleccion) >= MAX_ANIMACIONES:
            # Eliminar la más antigua (último elemento, orden desc)
            eliminada = coleccion[-1]
            await self.db.delete(eliminada)

        nueva = AnimacionGuardada(
            estudiante_id=estudiante_id,
            problema_id=problema_id,
            operacion=operacion,
            numero1=numero1,
            numero2=numero2,
            nivel_dificultad=nivel_dificultad,
            guardado_en=datetime.utcnow(),
        )
        self.db.add(nueva)
        await self.db.commit()
        await self.db.refresh(nueva)
        return nueva, eliminada

    async def eliminar(self, estudiante_id: int, animacion_id: int) -> bool:
        """
        Elimina una animación de la colección del estudiante.

        Verifica que la animación pertenezca al estudiante antes de eliminar.
        Returns True si se eliminó, False si no existía o no pertenece al estudiante.
        """
        result = await self.db.execute(
            select(AnimacionGuardada).where(
                AnimacionGuardada.id == animacion_id,
                AnimacionGuardada.estudiante_id == estudiante_id,
            )
        )
        animacion = result.scalar_one_or_none()
        if not animacion:
            return False
        await self.db.delete(animacion)
        await self.db.commit()
        return True

    async def count(self, estudiante_id: int) -> int:
        """Número de animaciones guardadas por el estudiante."""
        coleccion = await self.get_coleccion(estudiante_id)
        return len(coleccion)
