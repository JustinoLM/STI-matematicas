"""
Repository para enunciados narrativos temáticos.

Gestiona la caché de enunciados generados con LLM (tabla enunciado_tematico)
y provee acceso a Problema para obtener signature + nivel.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import EnunciadoTematico
from app.models.problem import Problema


class EnunciadoTematicoRepository:
    """Repository para caché de enunciados narrativos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────
    # Caché de enunciados
    # ──────────────────────────────────────────────────────────────

    async def get(
        self, signature: str, tema: str, nivel: int
    ) -> Optional[EnunciadoTematico]:
        """Busca un enunciado en caché. Retorna None si no existe."""
        result = await self.db.execute(
            select(EnunciadoTematico).where(
                EnunciadoTematico.signature == signature,
                EnunciadoTematico.tema == tema,
                EnunciadoTematico.nivel == nivel,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, signature: str, tema: str, nivel: int, texto: str
    ) -> EnunciadoTematico:
        """Crea y persiste un enunciado en caché."""
        obj = EnunciadoTematico(
            signature=signature,
            tema=tema,
            nivel=nivel,
            texto=texto,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    # ──────────────────────────────────────────────────────────────
    # Acceso a Problema
    # ──────────────────────────────────────────────────────────────

    async def get_problema(self, problema_id: int) -> Optional[Problema]:
        """Obtiene un Problema por ID para extraer signature y nivel."""
        result = await self.db.execute(
            select(Problema).where(Problema.id == problema_id)
        )
        return result.scalar_one_or_none()
