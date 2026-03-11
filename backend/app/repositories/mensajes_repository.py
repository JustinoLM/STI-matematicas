"""
Repositorio para mensajes motivacionales (caché diaria por estudiante).
"""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import MensajeMotivacional


class MensajesRepository:
    """Acceso a datos para MensajeMotivacional."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(
        self,
        estudiante_id: int,
        tipo: str,
        fecha: date,
        tema: Optional[str] = None,
    ) -> Optional[MensajeMotivacional]:
        """
        Busca mensaje en caché para (estudiante, tipo, fecha, tema).

        tema=None  → filtra por tema IS NULL (sin tema activo)
        tema='...' → filtra por ese tema exacto
        """
        if tema is None:
            tema_filter = MensajeMotivacional.tema.is_(None)
        else:
            tema_filter = MensajeMotivacional.tema == tema

        result = await self.db.execute(
            select(MensajeMotivacional).where(
                MensajeMotivacional.estudiante_id == estudiante_id,
                MensajeMotivacional.tipo == tipo,
                MensajeMotivacional.fecha == fecha,
                tema_filter,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        estudiante_id: int,
        tipo: str,
        texto: str,
        fecha: date,
        tema: Optional[str] = None,
    ) -> MensajeMotivacional:
        """Guarda nuevo mensaje en caché (incluye el tema activo)."""
        mensaje = MensajeMotivacional(
            estudiante_id=estudiante_id,
            tipo=tipo,
            texto=texto,
            fecha=fecha,
            tema=tema,
        )
        self.db.add(mensaje)
        await self.db.commit()
        await self.db.refresh(mensaje)
        return mensaje
