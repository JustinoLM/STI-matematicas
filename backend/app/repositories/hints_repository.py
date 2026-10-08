"""
Repository del sistema de pistas.

Registra el uso de pistas por estudiante y el historial de generaciones del LLM.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hints import GeneracionLLM, NivelPista, UsoPista


class HintsRepository:
    """Repository para pistas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar_uso_pista(
        self,
        estudiante_id: int,
        sesion_id: int,
        problema_id: int,
        nivel_pista: NivelPista,
        puntos_gastados: int,
        generada_llm: bool = False,
        contenido_pista: Optional[str] = None
    ) -> UsoPista:
        """Registra el uso de una pista."""
        uso = UsoPista(
            estudiante_id=estudiante_id,
            sesion_id=sesion_id,
            problema_id=problema_id,
            nivel_pista=nivel_pista,
            puntos_gastados=puntos_gastados,
            generada_llm=generada_llm,
            contenido_pista=contenido_pista,
            fecha=datetime.utcnow()
        )
        
        self.db.add(uso)
        await self.db.commit()
        await self.db.refresh(uso)
        
        return uso

    async def get_pistas_usadas_sesion(
        self,
        sesion_id: int,
        problema_id: int
    ) -> List[UsoPista]:
        """Obtiene las pistas ya usadas para un problema en una sesión."""
        result = await self.db.execute(
            select(UsoPista)
            .where(
                and_(
                    UsoPista.sesion_id == sesion_id,
                    UsoPista.problema_id == problema_id
                )
            )
            .order_by(UsoPista.nivel_pista)
        )
        return list(result.scalars().all())

    async def registrar_generacion_llm(
        self,
        tipo: str,
        prompt_usado: str,
        respuesta_llm: str,
        modelo: str,
        problema_id: Optional[int] = None,
        tema: Optional[str] = None,
        tokens_usados: Optional[int] = None,
        tiempo_generacion_ms: Optional[int] = None,
        exitoso: bool = True,
        error: Optional[str] = None
    ) -> GeneracionLLM:
        """Registra una generación con LLM para analytics."""
        generacion = GeneracionLLM(
            tipo=tipo,
            problema_id=problema_id,
            tema=tema,
            prompt_usado=prompt_usado,
            modelo=modelo,
            respuesta_llm=respuesta_llm,
            tokens_usados=tokens_usados,
            tiempo_generacion_ms=tiempo_generacion_ms,
            fecha=datetime.utcnow(),
            exitoso=exitoso,
            error=error
        )
        
        self.db.add(generacion)
        await self.db.commit()
        await self.db.refresh(generacion)
        
        return generacion
