"""
Repository para operaciones de gestión de prácticas.

Gestiona sesiones, progreso, historial y estadísticas.
"""

from typing import Optional, List, Dict
from sqlalchemy import select, func, and_, or_, desc, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.adaptive import SesionPractica, EstadoSesion, PerfilEstudiante
from app.models.problem import Intento, Problema


class PracticeRepository:
    """Repository para operaciones de prácticas e intentos."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================
    # Gestión de Sesiones Activas
    # ============================================
    
    async def get_active_session(self, estudiante_id: int) -> Optional[SesionPractica]:
        """
        Obtiene la sesión activa del estudiante.
        
        Activa = iniciada, en_progreso o pausada (no completada ni abandonada).
        """
        result = await self.db.execute(
            select(SesionPractica)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado.in_([
                        EstadoSesion.INICIADA,
                        EstadoSesion.EN_PROGRESO,
                        EstadoSesion.PAUSADA
                    ])
                )
            )
            .order_by(SesionPractica.fecha_inicio.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_sesion(self, sesion_id: int) -> Optional[SesionPractica]:
        """Obtiene una sesión por ID."""
        result = await self.db.execute(
            select(SesionPractica).where(SesionPractica.id == sesion_id)
        )
        return result.scalar_one_or_none()
    
    async def update_sesion(self, sesion: SesionPractica) -> SesionPractica:
        """Actualiza una sesión."""
        sesion.fecha_ultima_actividad = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(sesion)
        return sesion
    
    async def marcar_como_abandonada(self, sesion: SesionPractica) -> None:
        """Marca sesión como abandonada."""
        sesion.estado = EstadoSesion.ABANDONADA
        sesion.fecha_fin = datetime.utcnow()
        await self.update_sesion(sesion)
    
    async def verificar_timeout_sesiones(self, estudiante_id: int) -> None:
        """
        Marca como abandonadas las sesiones pausadas por más de 4 horas.
        """
        timeout = datetime.utcnow() - timedelta(hours=4)
        
        result = await self.db.execute(
            select(SesionPractica)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.PAUSADA,
                    SesionPractica.fecha_ultima_actividad < timeout
                )
            )
        )
        
        sesiones_timeout = result.scalars().all()
        
        for sesion in sesiones_timeout:
            await self.marcar_como_abandonada(sesion)
    
    # ============================================
    # Progreso de Sesión
    # ============================================
    
    async def incrementar_progreso(self, sesion: SesionPractica) -> None:
        """Incrementa el progreso de la sesión en 1."""
        sesion.progreso_actual += 1
        sesion.estado = EstadoSesion.EN_PROGRESO
        await self.update_sesion(sesion)
    
    async def get_intentos_sesion_actual(
        self,
        sesion_id: int,
        problema_id: int
    ) -> List[Intento]:
        """Obtiene intentos del problema actual en la sesión."""
        result = await self.db.execute(
            select(Intento)
            .where(
                and_(
                    Intento.sesion_id == sesion_id,
                    Intento.problema_id == problema_id
                )
            )
            .order_by(Intento.timestamp.asc())
        )
        return list(result.scalars().all())
    
    async def count_intentos_problema(
        self,
        sesion_id: int,
        problema_id: int
    ) -> int:
        """Cuenta cuántos intentos se han hecho en un problema específico."""
        result = await self.db.execute(
            select(func.count(Intento.id))
            .where(
                and_(
                    Intento.sesion_id == sesion_id,
                    Intento.problema_id == problema_id
                )
            )
        )
        return result.scalar() or 0
    
    # ============================================
    # Historial de Sesiones
    # ============================================
    
    async def get_session_history(
        self,
        estudiante_id: int,
        limit: int = 20,
        skip: int = 0
    ) -> List[SesionPractica]:
        """
        Obtiene historial de sesiones del estudiante.
        
        Ordenadas por fecha descendente (más reciente primero).
        """
        result = await self.db.execute(
            select(SesionPractica)
            .where(SesionPractica.estudiante_id == estudiante_id)
            .order_by(SesionPractica.fecha_inicio.desc())
            .limit(limit)
            .offset(skip)
        )
        return list(result.scalars().all())
    
    async def count_total_sessions(self, estudiante_id: int) -> int:
        """Cuenta total de sesiones del estudiante."""
        result = await self.db.execute(
            select(func.count(SesionPractica.id))
            .where(SesionPractica.estudiante_id == estudiante_id)
        )
        return result.scalar() or 0
    
    async def count_completed_sessions(self, estudiante_id: int) -> int:
        """Cuenta sesiones completadas."""
        result = await self.db.execute(
            select(func.count(SesionPractica.id))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
        )
        return result.scalar() or 0
    
    # ============================================
    # Estadísticas Globales
    # ============================================
    
    async def get_total_problemas_resueltos(self, estudiante_id: int) -> int:
        """Total de problemas resueltos (sesiones completadas)."""
        result = await self.db.execute(
            select(func.sum(SesionPractica.cantidad_problemas))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
        )
        return result.scalar() or 0
    
    async def get_total_problemas_correctos(self, estudiante_id: int) -> int:
        """Total de problemas correctos."""
        result = await self.db.execute(
            select(func.sum(SesionPractica.problemas_correctos))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
        )
        return result.scalar() or 0
    
    async def get_racha_actual_perfectas(self, estudiante_id: int) -> int:
        """
        Calcula racha actual de sesiones perfectas consecutivas.
        
        Cuenta desde la última sesión hacia atrás mientras sean perfectas.
        """
        result = await self.db.execute(
            select(SesionPractica.es_practica_perfecta)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
            .order_by(SesionPractica.fecha_inicio.desc())
            .limit(50)  # Verificar últimas 50
        )
        
        sesiones = result.scalars().all()
        
        racha = 0
        for es_perfecta in sesiones:
            if es_perfecta:
                racha += 1
            else:
                break
        
        return racha
    
    async def get_mejor_racha_perfectas(self, estudiante_id: int) -> int:
        """
        Calcula la mejor racha histórica de sesiones perfectas.
        """
        result = await self.db.execute(
            select(SesionPractica.es_practica_perfecta)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
            .order_by(SesionPractica.fecha_inicio.asc())
        )
        
        sesiones = result.scalars().all()
        
        racha_actual = 0
        mejor_racha = 0
        
        for es_perfecta in sesiones:
            if es_perfecta:
                racha_actual += 1
                mejor_racha = max(mejor_racha, racha_actual)
            else:
                racha_actual = 0
        
        return mejor_racha
    
    async def get_sesiones_ultimos_n_dias(
        self,
        estudiante_id: int,
        dias: int = 7
    ) -> List[SesionPractica]:
        """Obtiene sesiones de los últimos N días."""
        fecha_limite = datetime.utcnow() - timedelta(days=dias)
        
        result = await self.db.execute(
            select(SesionPractica)
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.fecha_inicio >= fecha_limite,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
            .order_by(SesionPractica.fecha_inicio.asc())
        )
        
        return list(result.scalars().all())
    
    async def get_dias_consecutivos_practicando(self, estudiante_id: int) -> int:
        """
        Calcula días consecutivos que el estudiante ha practicado.
        
        Cuenta desde hoy hacia atrás mientras haya al menos una sesión por día.
        """
        result = await self.db.execute(
            select(func.date(SesionPractica.fecha_inicio).label('fecha'))
            .where(
                and_(
                    SesionPractica.estudiante_id == estudiante_id,
                    SesionPractica.estado == EstadoSesion.COMPLETADA
                )
            )
            .group_by(func.date(SesionPractica.fecha_inicio))
            .order_by(desc('fecha'))
        )
        
        fechas = [row[0] for row in result.all()]
        
        if not fechas:
            return 0
        
        # Contar días consecutivos desde hoy
        dias_consecutivos = 0
        fecha_esperada = datetime.utcnow().date()
        
        for fecha in fechas:
            if fecha == fecha_esperada:
                dias_consecutivos += 1
                fecha_esperada -= timedelta(days=1)
            else:
                break
        
        return dias_consecutivos
    
    # ============================================
    # Detección de Anomalías
    # ============================================
    
    async def get_velocidades_grupo(self, grupo_id: int) -> List[float]:
        """
        Obtiene velocidades promedio de todos los estudiantes del grupo.
        
        Usado para detectar outliers.
        """
        # TODO: Implementar cuando tengamos relación estudiante-grupo
        # Por ahora retorna lista vacía
        return []
    
    async def get_stats_por_operacion(self, estudiante_id: int) -> Dict:
        """
        Estadísticas de intentos agrupadas por operación.

        Retorna dict con símbolo del enum como clave (+, -, ×, ÷) y dict de métricas.
        """
        result = await self.db.execute(
            select(
                Problema.operacion,
                func.count(Intento.id).label('total_intentos'),
                func.sum(case((Intento.es_correcto == True, 1), else_=0)).label('total_correctos'),
                func.count(distinct(Intento.problema_id)).label('problemas_resueltos'),
                func.avg(Intento.tiempo_resolucion).label('velocidad_promedio'),
            )
            .join(Problema, Intento.problema_id == Problema.id)
            .where(Intento.estudiante_id == estudiante_id)
            .group_by(Problema.operacion)
        )

        stats: Dict = {}
        for row in result.all():
            stats[row.operacion] = {
                'total_intentos': row.total_intentos or 0,
                'total_correctos': int(row.total_correctos or 0),
                'problemas_resueltos': row.problemas_resueltos or 0,
                'velocidad_promedio': float(row.velocidad_promedio or 0.0),
            }
        return stats

    async def marcar_sesion_sospechosa(
        self,
        sesion: SesionPractica,
        patron_sospechoso: bool = True,
        velocidad_sospechosa: bool = False
    ) -> None:
        """Marca sesión como sospechosa."""
        sesion.patron_sospechoso = patron_sospechoso
        sesion.velocidad_sospechosa = velocidad_sospechosa
        await self.update_sesion(sesion)
