"""
Repository para operaciones de base de datos del módulo de Regla de Tres.

Gestiona perfil adaptativo, problemas, sesiones e intentos — todo
independiente del sistema de las 4 operaciones base.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regla_de_tres import (
    PerfilReglaTres,
    ProblemaReglaTres,
    SesionPracticaReglaTres,
    IntentoReglaTres,
    EstadoSesion,
)
from app.models.user import Estudiante


class ReglaDeTresRepository:
    """Repository para operaciones del módulo de Regla de Tres."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================
    # Operaciones de Perfil
    # ============================================

    async def get_perfil(self, estudiante_id: int) -> Optional[PerfilReglaTres]:
        result = await self.db.execute(
            select(PerfilReglaTres).where(PerfilReglaTres.estudiante_id == estudiante_id)
        )
        return result.scalar_one_or_none()

    async def create_perfil(self, estudiante_id: int) -> PerfilReglaTres:
        perfil = PerfilReglaTres(estudiante_id=estudiante_id, nivel_actual=1)
        self.db.add(perfil)
        await self.db.commit()
        await self.db.refresh(perfil)
        return perfil

    async def get_or_create_perfil(self, estudiante_id: int) -> PerfilReglaTres:
        perfil = await self.get_perfil(estudiante_id)
        if perfil:
            return perfil
        try:
            return await self.create_perfil(estudiante_id)
        except IntegrityError:
            # Carrera: otra request ya creó el perfil entre el get y el create
            await self.db.rollback()
            perfil = await self.get_perfil(estudiante_id)
            if perfil:
                return perfil
            raise

    async def update_perfil(self, perfil: PerfilReglaTres) -> PerfilReglaTres:
        await self.db.commit()
        await self.db.refresh(perfil)
        return perfil

    # ============================================
    # Operaciones de Problema
    # ============================================

    async def get_problema_by_signature(self, signature: str) -> Optional[ProblemaReglaTres]:
        result = await self.db.execute(
            select(ProblemaReglaTres).where(ProblemaReglaTres.signature == signature)
        )
        return result.scalar_one_or_none()

    async def get_problema(self, problema_id: int) -> Optional[ProblemaReglaTres]:
        result = await self.db.execute(
            select(ProblemaReglaTres).where(ProblemaReglaTres.id == problema_id)
        )
        return result.scalar_one_or_none()

    async def create_problema(self, problema: ProblemaReglaTres) -> ProblemaReglaTres:
        self.db.add(problema)
        await self.db.commit()
        await self.db.refresh(problema)
        return problema

    # ============================================
    # Operaciones de Sesión
    # ============================================

    async def create_sesion(self, sesion: SesionPracticaReglaTres) -> SesionPracticaReglaTres:
        self.db.add(sesion)
        await self.db.commit()
        await self.db.refresh(sesion)
        return sesion

    async def get_sesion(self, sesion_id: int) -> Optional[SesionPracticaReglaTres]:
        result = await self.db.execute(
            select(SesionPracticaReglaTres).where(SesionPracticaReglaTres.id == sesion_id)
        )
        return result.scalar_one_or_none()

    async def update_sesion(self, sesion: SesionPracticaReglaTres) -> SesionPracticaReglaTres:
        await self.db.commit()
        await self.db.refresh(sesion)
        return sesion

    async def get_ultima_sesion_completada(self, estudiante_id: int) -> Optional[SesionPracticaReglaTres]:
        result = await self.db.execute(
            select(SesionPracticaReglaTres)
            .where(
                SesionPracticaReglaTres.estudiante_id == estudiante_id,
                SesionPracticaReglaTres.estado == EstadoSesion.COMPLETADA,
            )
            .order_by(SesionPracticaReglaTres.fecha_fin.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ============================================
    # Operaciones de Intento
    # ============================================

    async def create_intento(self, intento: IntentoReglaTres) -> IntentoReglaTres:
        self.db.add(intento)
        await self.db.commit()
        await self.db.refresh(intento)
        return intento

    # ============================================
    # Notas por estudiante (profesor / admin)
    # ============================================

    async def get_notas_por_estudiantes(self, estudiante_ids: List[int]) -> List[dict]:
        """
        Devuelve, por cada estudiante_id dado, sus datos básicos + la última
        sesión completada de regla de tres (o None si nunca practicó).
        """
        if not estudiante_ids:
            return []

        est_result = await self.db.execute(
            select(Estudiante.id, Estudiante.codigo_estudiante, Estudiante.nombre_completo)
            .where(Estudiante.id.in_(estudiante_ids))
            .order_by(Estudiante.nombre_completo)
        )
        estudiantes = est_result.all()

        perfiles_result = await self.db.execute(
            select(PerfilReglaTres).where(PerfilReglaTres.estudiante_id.in_(estudiante_ids))
        )
        perfil_por_estudiante = {p.estudiante_id: p for p in perfiles_result.scalars().all()}

        sesiones_result = await self.db.execute(
            select(SesionPracticaReglaTres)
            .where(
                SesionPracticaReglaTres.estudiante_id.in_(estudiante_ids),
                SesionPracticaReglaTres.estado == EstadoSesion.COMPLETADA,
            )
            .order_by(SesionPracticaReglaTres.fecha_fin.desc())
        )
        ultima_sesion_por_estudiante = {}
        for sesion in sesiones_result.scalars().all():
            if sesion.estudiante_id not in ultima_sesion_por_estudiante:
                ultima_sesion_por_estudiante[sesion.estudiante_id] = sesion

        filas = []
        for est_id, codigo, nombre in estudiantes:
            sesion = ultima_sesion_por_estudiante.get(est_id)
            perfil = perfil_por_estudiante.get(est_id)
            if sesion:
                total = sesion.problemas_correctos + sesion.problemas_incorrectos
                filas.append({
                    "estudiante_id": est_id,
                    "codigo": codigo,
                    "nombre_completo": nombre,
                    "tiene_practica": True,
                    "ultima_fecha": sesion.fecha_fin,
                    "correctos": sesion.problemas_correctos,
                    "total": total,
                    "nota_pct": round(sesion.problemas_correctos / total * 100, 1) if total else 0.0,
                    "nivel_actual": perfil.nivel_actual if perfil else sesion.nivel_al_iniciar,
                })
            else:
                filas.append({
                    "estudiante_id": est_id,
                    "codigo": codigo,
                    "nombre_completo": nombre,
                    "tiene_practica": False,
                    "ultima_fecha": None,
                    "correctos": None,
                    "total": None,
                    "nota_pct": None,
                    "nivel_actual": perfil.nivel_actual if perfil else None,
                })
        return filas
