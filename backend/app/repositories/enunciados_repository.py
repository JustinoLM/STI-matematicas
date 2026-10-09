"""
Repository para enunciados narrativos temáticos.

Gestiona la caché de enunciados generados con LLM (tabla enunciado_tematico)
y provee acceso a Problema para obtener signature + nivel.
"""

from typing import List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import EnunciadoTematico
from app.models.adaptive import SesionPractica
from app.models.problem import Problema


class EnunciadoTematicoRepository:
    """Repository para caché de enunciados narrativos."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────
    # Caché de enunciados
    # ──────────────────────────────────────────────────────────────

    async def get_variaciones(
        self, signature: str, tema: str, nivel: int
    ) -> List[EnunciadoTematico]:
        """Enunciados en caché de un problema+tema (vacío si no hay ninguno)."""
        result = await self.db.execute(
            select(EnunciadoTematico)
            .where(
                EnunciadoTematico.signature == signature,
                EnunciadoTematico.tema == tema,
                EnunciadoTematico.nivel == nivel,
            )
            .order_by(EnunciadoTematico.variacion)
        )
        return list(result.scalars().all())

    async def guardar_variaciones(
        self, signature: str, tema: str, nivel: int, textos: List[str]
    ) -> None:
        """Persiste los textos como variaciones 1..N."""
        for i, texto in enumerate(textos, start=1):
            self.db.add(
                EnunciadoTematico(
                    signature=signature, tema=tema, nivel=nivel, variacion=i, texto=texto
                )
            )
        await self.db.commit()

    # ──────────────────────────────────────────────────────────────
    # Acceso a Problema
    # ──────────────────────────────────────────────────────────────

    async def get_problema(self, problema_id: int) -> Optional[Problema]:
        """Obtiene un Problema por ID para extraer signature y nivel."""
        result = await self.db.execute(
            select(Problema).where(Problema.id == problema_id)
        )
        return result.scalar_one_or_none()

    async def get_ids_problemas_del_estudiante(
        self, estudiante_id: int, ultimas_sesiones: int = 20
    ) -> Set[int]:
        """Ids de los problemas de las últimas sesiones del estudiante."""
        result = await self.db.execute(
            select(SesionPractica.problemas_ids)
            .where(SesionPractica.estudiante_id == estudiante_id)
            .order_by(SesionPractica.fecha_inicio.desc())
            .limit(ultimas_sesiones)
        )
        ids: Set[int] = set()
        for lista in result.scalars().all():
            ids.update(int(i) for i in (lista or []))
        return ids
