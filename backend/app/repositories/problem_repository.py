"""
Repository para operaciones de base de datos de problemas.

Gestiona problemas matemáticos, configuraciones y intentos.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.problem import Intento, Operacion, Problema, TipoSesion


class ProblemRepository:
    """Repository para operaciones CRUD de problemas."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================
    # Operaciones de Problemas
    # ============================================
    
    async def create_problem(
        self,
        operacion: Operacion,
        numero1: Decimal,
        numero2: Decimal,
        resultado: Decimal,
        nivel_dificultad: int,
        cantidad_decimales: int,
        signature: str
    ) -> Problema:
        """Crea un nuevo problema."""
        problema = Problema(
            operacion=operacion,
            numero1=numero1,
            numero2=numero2,
            resultado=resultado,
            nivel_dificultad=nivel_dificultad,
            cantidad_decimales=cantidad_decimales,
            signature=signature
        )
        
        self.db.add(problema)
        await self.db.commit()
        await self.db.refresh(problema)
        
        return problema
    
    async def get_problem_by_id(self, problema_id: int) -> Optional[Problema]:
        """Obtiene un problema por ID."""
        result = await self.db.execute(
            select(Problema).where(Problema.id == problema_id)
        )
        return result.scalar_one_or_none()
    
    async def get_problem_by_signature(self, signature: str) -> Optional[Problema]:
        """Busca un problema por su signature (evita duplicados)."""
        result = await self.db.execute(
            select(Problema).where(Problema.signature == signature)
        )
        return result.scalar_one_or_none()
    
    # ============================================
    # Operaciones de Configuración
    # ============================================
    
    # ============================================
    # Operaciones de Intentos
    # ============================================
    
    async def create_intento(
        self,
        estudiante_id: int,
        problema_id: int,
        respuesta_estudiante: Decimal,
        es_correcto: bool,
        tiempo_resolucion: int,
        solicito_pista: bool,
        tipo_sesion: TipoSesion,
        sesion_id: Optional[int] = None
    ) -> Intento:
        """Registra un intento de resolver un problema."""
        intento = Intento(
            estudiante_id=estudiante_id,
            problema_id=problema_id,
            respuesta_estudiante=respuesta_estudiante,
            es_correcto=es_correcto,
            tiempo_resolucion=tiempo_resolucion,
            solicito_pista=solicito_pista,
            tipo_sesion=tipo_sesion,
            sesion_id=sesion_id
        )
        
        self.db.add(intento)
        await self.db.commit()
        await self.db.refresh(intento)
        
        return intento
    
