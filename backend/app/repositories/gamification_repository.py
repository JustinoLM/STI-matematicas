"""
Repository para operaciones de gamificación.

Gestiona desbloqueables, medallas, puntos y personalización.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import (
    CategoriaDesbloqueable,
    Desbloqueable,
    EstudianteDesbloqueable,
    EstudianteMedalla,
    Medalla,
    PersonalizacionEstudiante,
    TipoTransaccion,
    TransaccionPuntos,
)
from app.models.user import Estudiante


class GamificationRepository:
    """Repository para operaciones de gamificación."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================
    # Gestión de Puntos
    # ============================================
    
    async def get_saldo_puntos(self, estudiante_id: int) -> int:
        """Obtiene el saldo actual de puntos del estudiante."""
        result = await self.db.execute(
            select(Estudiante.puntos_totales)
            .where(Estudiante.id == estudiante_id)
        )
        return result.scalar() or 0
    
    async def agregar_puntos(
        self,
        estudiante_id: int,
        cantidad: int,
        concepto: str,
        sesion_id: Optional[int] = None
    ) -> int:
        """
        Agrega puntos al estudiante y registra la transacción.
        
        Returns:
            Nuevo saldo
        """
        # Obtener estudiante
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.id == estudiante_id)
        )
        estudiante = result.scalar_one()
        
        # Actualizar saldo
        estudiante.puntos_totales += cantidad
        nuevo_saldo = estudiante.puntos_totales
        
        # Registrar transacción
        transaccion = TransaccionPuntos(
            estudiante_id=estudiante_id,
            tipo=TipoTransaccion.GANANCIA,
            cantidad=cantidad,
            concepto=concepto,
            sesion_id=sesion_id,
            saldo_resultante=nuevo_saldo,
            fecha=datetime.utcnow()
        )
        
        self.db.add(transaccion)
        await self.db.commit()
        await self.db.refresh(estudiante)
        
        return nuevo_saldo
    
    async def gastar_puntos(
        self,
        estudiante_id: int,
        cantidad: int,
        concepto: str,
        desbloqueable_id: Optional[int] = None
    ) -> int:
        """
        Gasta puntos del estudiante y registra la transacción.
        
        Raises:
            ValueError si no tiene suficientes puntos.
        
        Returns:
            Nuevo saldo
        """
        # Obtener estudiante
        result = await self.db.execute(
            select(Estudiante).where(Estudiante.id == estudiante_id)
        )
        estudiante = result.scalar_one()
        
        # Verificar saldo
        if estudiante.puntos_totales < cantidad:
            raise ValueError(
                f"Saldo insuficiente. Tiene {estudiante.puntos_totales} puntos, necesita {cantidad}"
            )
        
        # Actualizar saldo
        estudiante.puntos_totales -= cantidad
        nuevo_saldo = estudiante.puntos_totales
        
        # Registrar transacción
        transaccion = TransaccionPuntos(
            estudiante_id=estudiante_id,
            tipo=TipoTransaccion.GASTO,
            cantidad=cantidad,
            concepto=concepto,
            desbloqueable_id=desbloqueable_id,
            saldo_resultante=nuevo_saldo,
            fecha=datetime.utcnow()
        )
        
        self.db.add(transaccion)
        await self.db.commit()
        await self.db.refresh(estudiante)
        
        return nuevo_saldo
    
    async def get_historial_transacciones(
        self,
        estudiante_id: int,
        limit: int = 50
    ) -> List[TransaccionPuntos]:
        """Obtiene historial de transacciones del estudiante."""
        result = await self.db.execute(
            select(TransaccionPuntos)
            .where(TransaccionPuntos.estudiante_id == estudiante_id)
            .order_by(TransaccionPuntos.fecha.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ============================================
    # Gestión de Desbloqueables
    # ============================================
    
    async def get_catalogo_completo(self) -> List[Desbloqueable]:
        """Obtiene todos los desbloqueables activos."""
        result = await self.db.execute(
            select(Desbloqueable)
            .where(Desbloqueable.activo == True)
            .order_by(Desbloqueable.categoria, Desbloqueable.orden)
        )
        return list(result.scalars().all())
    
    async def get_desbloqueable(self, desbloqueable_id: int) -> Optional[Desbloqueable]:
        """Obtiene un desbloqueable por ID."""
        result = await self.db.execute(
            select(Desbloqueable).where(Desbloqueable.id == desbloqueable_id)
        )
        return result.scalar_one_or_none()
    
    async def get_temas_iniciales(self) -> List[Desbloqueable]:
        """Obtiene los temas marcados como iniciales (gratis)."""
        result = await self.db.execute(
            select(Desbloqueable)
            .where(
                and_(
                    Desbloqueable.categoria == CategoriaDesbloqueable.TEMA,
                    Desbloqueable.es_tema_inicial == True,
                    Desbloqueable.activo == True
                )
            )
            .order_by(Desbloqueable.orden)
        )
        return list(result.scalars().all())
    
    async def estudiante_posee_item(
        self,
        estudiante_id: int,
        desbloqueable_id: int
    ) -> bool:
        """Verifica si el estudiante ya posee un item."""
        result = await self.db.execute(
            select(func.count(EstudianteDesbloqueable.id))
            .where(
                and_(
                    EstudianteDesbloqueable.estudiante_id == estudiante_id,
                    EstudianteDesbloqueable.desbloqueable_id == desbloqueable_id
                )
            )
        )
        count = result.scalar() or 0
        return count > 0
    
    async def get_items_poseidos(self, estudiante_id: int) -> List[EstudianteDesbloqueable]:
        """Obtiene todos los items que posee el estudiante."""
        result = await self.db.execute(
            select(EstudianteDesbloqueable)
            .where(EstudianteDesbloqueable.estudiante_id == estudiante_id)
        )
        return list(result.scalars().all())
    
    async def get_ids_desbloqueables_activos(self) -> set[int]:
        """Ids de los items activos del catálogo de la tienda."""
        result = await self.db.execute(
            select(Desbloqueable.id).where(Desbloqueable.activo.is_(True))
        )
        return set(result.scalars().all())

    async def desbloquear_item(
        self,
        estudiante_id: int,
        desbloqueable_id: int,
        puntos_gastados: int
    ) -> EstudianteDesbloqueable:
        """Registra que el estudiante desbloqueó un item."""
        relacion = EstudianteDesbloqueable(
            estudiante_id=estudiante_id,
            desbloqueable_id=desbloqueable_id,
            fecha_compra=datetime.utcnow(),
            puntos_gastados=puntos_gastados
        )
        
        self.db.add(relacion)
        await self.db.commit()
        await self.db.refresh(relacion)
        
        return relacion
    
    # ============================================
    # Gestión de Medallas
    # ============================================
    
    async def get_todas_medallas(self) -> List[Medalla]:
        """Obtiene todas las medallas activas."""
        result = await self.db.execute(
            select(Medalla)
            .where(Medalla.activa == True)
            .order_by(Medalla.categoria, Medalla.orden)
        )
        return list(result.scalars().all())
    
    async def estudiante_tiene_medalla(
        self,
        estudiante_id: int,
        medalla_id: int
    ) -> bool:
        """Verifica si el estudiante ya tiene una medalla."""
        result = await self.db.execute(
            select(func.count(EstudianteMedalla.id))
            .where(
                and_(
                    EstudianteMedalla.estudiante_id == estudiante_id,
                    EstudianteMedalla.medalla_id == medalla_id
                )
            )
        )
        count = result.scalar() or 0
        return count > 0
    
    async def get_medallas_estudiante(
        self,
        estudiante_id: int
    ) -> List[EstudianteMedalla]:
        """Obtiene todas las medallas que el estudiante ha ganado."""
        result = await self.db.execute(
            select(EstudianteMedalla)
            .where(EstudianteMedalla.estudiante_id == estudiante_id)
            .order_by(EstudianteMedalla.fecha_obtencion.desc())
        )
        return list(result.scalars().all())
    
    async def otorgar_medalla(
        self,
        estudiante_id: int,
        medalla_id: int
    ) -> EstudianteMedalla:
        """Otorga una medalla al estudiante."""
        relacion = EstudianteMedalla(
            estudiante_id=estudiante_id,
            medalla_id=medalla_id,
            fecha_obtencion=datetime.utcnow(),
            notificada=False
        )
        
        self.db.add(relacion)
        await self.db.commit()
        await self.db.refresh(relacion)
        
        return relacion
    
    # ============================================
    # Gestión de Personalización
    # ============================================
    
    async def get_personalizacion(
        self,
        estudiante_id: int
    ) -> Optional[PersonalizacionEstudiante]:
        """Obtiene la configuración de personalización del estudiante."""
        result = await self.db.execute(
            select(PersonalizacionEstudiante)
            .where(PersonalizacionEstudiante.estudiante_id == estudiante_id)
        )
        return result.scalar_one_or_none()
    
    async def crear_personalizacion(
        self,
        estudiante_id: int
    ) -> PersonalizacionEstudiante:
        """Crea configuración de personalización por defecto."""
        personalizacion = PersonalizacionEstudiante(
            estudiante_id=estudiante_id,
            tema_activo_id=None,
            fondo_activo_id=None,
            musica_activa_id=None,
            color_fondo="#FFFFFF",
            color_texto="#000000",
            color_botones="#007AFF",
            efectos_activos=[],
            fecha_actualizacion=datetime.utcnow()
        )
        
        self.db.add(personalizacion)
        await self.db.commit()
        await self.db.refresh(personalizacion)
        
        return personalizacion
    
    async def actualizar_personalizacion(
        self,
        estudiante_id: int,
        **campos
    ) -> PersonalizacionEstudiante:
        """Actualiza la configuración de personalización."""
        result = await self.db.execute(
            select(PersonalizacionEstudiante)
            .where(PersonalizacionEstudiante.estudiante_id == estudiante_id)
        )
        personalizacion = result.scalar_one_or_none()
        
        if not personalizacion:
            # Crear si no existe
            personalizacion = await self.crear_personalizacion(estudiante_id)
        
        # Actualizar campos
        for key, value in campos.items():
            if value is not None and hasattr(personalizacion, key):
                setattr(personalizacion, key, value)
        
        personalizacion.fecha_actualizacion = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(personalizacion)
        
        return personalizacion
