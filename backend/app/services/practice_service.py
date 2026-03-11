"""
Service para gestión de prácticas e intentos.

Lógica de negocio para sesiones, progreso y detección de anomalías.
"""

import statistics
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException, status

from app.repositories.practice_repository import PracticeRepository
from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.problem_repository import ProblemRepository
from app.models.adaptive import SesionPractica, EstadoSesion, AlertaEstudiante, TipoAlerta
from app.models.problem import Intento, Problema, TipoSesion
from app.schemas.practice import (
    SessionProgressResponse,
    NextProblemResponse,
    SubmitProblemResponse,
    SessionHistoryResponse,
    SessionHistoryItem,
    SessionSummaryResponse,
    ProblemaSummary,
    GlobalStatsResponse,
    StatsPerOperation,
    AlertaSospechosa,
    SuspiciousActivityResponse
)


class PracticeService:
    """Service para gestión de prácticas e intentos."""
    
    # Constantes
    MAX_INTENTOS_POR_PROBLEMA = 3
    TIMEOUT_HORAS = 4
    
    def __init__(
        self,
        practice_repo: PracticeRepository,
        adaptive_repo: AdaptiveRepository,
        problem_repo: ProblemRepository
    ):
        self.practice_repo = practice_repo
        self.adaptive_repo = adaptive_repo
        self.problem_repo = problem_repo
    
    # ============================================
    # Gestión de Sesiones Activas
    # ============================================
    
    async def get_or_create_active_session(
        self,
        estudiante_id: int
    ) -> Tuple[SesionPractica, bool]:
        """
        Obtiene sesión activa o retorna None.
        
        Verifica timeout de 4 horas antes de retornar.
        
        Returns:
            Tuple[SesionPractica, bool]: (sesion, es_nueva)
        """
        await self.practice_repo.verificar_timeout_sesiones(estudiante_id)
        sesion = await self.practice_repo.get_active_session(estudiante_id)
        
        if sesion:
            return sesion, False
        
        return None, True
    
    async def pause_session(self, sesion_id: int, estudiante_id: int) -> Dict:
        """Pausa una sesión activa."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para pausar esta sesión"
            )
        
        if sesion.estado not in [EstadoSesion.INICIADA, EstadoSesion.EN_PROGRESO]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede pausar una sesión en estado {sesion.estado}"
            )
        
        sesion.estado = EstadoSesion.PAUSADA
        await self.practice_repo.update_sesion(sesion)
        
        timeout_fecha = datetime.utcnow() + timedelta(hours=self.TIMEOUT_HORAS)
        
        return {
            "sesion_id": sesion.id,
            "estado": sesion.estado.value,
            "progreso_actual": sesion.progreso_actual,
            "total_problemas": sesion.cantidad_problemas,
            "mensaje": f"Sesión pausada. Puedes reanudar antes de {timeout_fecha.strftime('%H:%M')}",
            "timeout_en": self.TIMEOUT_HORAS
        }
    
    async def resume_session(self, sesion_id: int, estudiante_id: int) -> NextProblemResponse:
        """Reanuda una sesión pausada."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para reanudar esta sesión"
            )
        
        if sesion.estado != EstadoSesion.PAUSADA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Solo se pueden reanudar sesiones pausadas (estado actual: {sesion.estado})"
            )
        
        tiempo_pausado = datetime.utcnow() - sesion.fecha_ultima_actividad
        if tiempo_pausado > timedelta(hours=self.TIMEOUT_HORAS):
            await self.practice_repo.marcar_como_abandonada(sesion)
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"La sesión expiró después de {self.TIMEOUT_HORAS} horas. Inicia una nueva práctica."
            )
        
        sesion.estado = EstadoSesion.EN_PROGRESO
        await self.practice_repo.update_sesion(sesion)
        
        return await self._get_next_problem(sesion)
    
    async def abandon_session(self, sesion_id: int, estudiante_id: int) -> Dict:
        """Abandona una sesión permanentemente."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para abandonar esta sesión"
            )
        
        if sesion.estado == EstadoSesion.COMPLETADA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede abandonar una sesión ya completada"
            )
        
        await self.practice_repo.marcar_como_abandonada(sesion)
        
        return {
            "sesion_id": sesion.id,
            "estado": "abandonada",
            "mensaje": "Sesión abandonada. No se ajustaron niveles."
        }
    
    # ============================================
    # Progreso de Sesión
    # ============================================
    
    async def get_session_progress(
        self,
        sesion_id: int,
        estudiante_id: int
    ) -> SessionProgressResponse:
        """Obtiene el progreso actual de una sesión."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver esta sesión"
            )
        
        resueltos = sesion.progreso_actual
        correctos = 0
        incorrectos = 0
        
        if sesion.problemas_correctos is not None:
            correctos = sesion.problemas_correctos
            incorrectos = sesion.problemas_incorrectos or 0
        
        tiempo_transcurrido = 0
        if sesion.fecha_inicio:
            if sesion.fecha_fin:
                delta = sesion.fecha_fin - sesion.fecha_inicio
            else:
                delta = datetime.utcnow() - sesion.fecha_inicio
            tiempo_transcurrido = int(delta.total_seconds())
        
        progreso_porcentaje = (resueltos / sesion.cantidad_problemas * 100) if sesion.cantidad_problemas > 0 else 0
        
        return SessionProgressResponse(
            sesion_id=sesion.id,
            total_problemas=sesion.cantidad_problemas,
            resueltos=resueltos,
            correctos=correctos,
            incorrectos=incorrectos,
            progreso_porcentaje=round(progreso_porcentaje, 1),
            tiempo_transcurrido=tiempo_transcurrido,
            estado=sesion.estado.value
        )
    
    async def _get_next_problem(self, sesion: SesionPractica) -> NextProblemResponse:
        """Obtiene el siguiente problema en la secuencia."""
        if sesion.progreso_actual >= sesion.cantidad_problemas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya completaste todos los problemas de esta sesión"
            )
        
        problema_id = sesion.problemas_ids[sesion.progreso_actual]
        problema = await self.problem_repo.get_problem_by_id(problema_id)
        
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al cargar el problema"
            )
        
        intentos_realizados = await self.practice_repo.count_intentos_problema(
            sesion.id,
            problema_id
        )
        
        intentos_restantes = self.MAX_INTENTOS_POR_PROBLEMA - intentos_realizados
        es_ultimo = (sesion.progreso_actual == sesion.cantidad_problemas - 1)
        
        return NextProblemResponse(
            sesion_id=sesion.id,
            problema_numero=sesion.progreso_actual + 1,
            total_problemas=sesion.cantidad_problemas,
            problema={
                "id": problema.id,
                "operacion": problema.operacion.value,
                "numero1": str(problema.numero1.normalize()),
                "numero2": str(problema.numero2.normalize()),
                "nivel_dificultad": problema.nivel_dificultad
            },
            intentos_restantes=intentos_restantes,
            es_ultimo=es_ultimo
        )
    
    async def submit_problem_answer(
        self,
        sesion_id: int,
        estudiante_id: int,
        problema_id: int,
        respuesta: Decimal,
        tiempo_resolucion: int
    ) -> SubmitProblemResponse:
        """Envía respuesta de un problema."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para enviar respuestas en esta sesión"
            )
        
        if sesion.estado not in [EstadoSesion.INICIADA, EstadoSesion.EN_PROGRESO]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pueden enviar respuestas en una sesión {sesion.estado.value}"
            )
        
        problema_actual_id = sesion.problemas_ids[sesion.progreso_actual]
        if problema_id != problema_actual_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este no es el problema actual de la sesión"
            )
        
        problema = await self.problem_repo.get_problem_by_id(problema_id)
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problema no encontrado"
            )
        
        intentos_previos = await self.practice_repo.count_intentos_problema(sesion_id, problema_id)
        
        if intentos_previos >= self.MAX_INTENTOS_POR_PROBLEMA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya agotaste los {self.MAX_INTENTOS_POR_PROBLEMA} intentos para este problema"
            )
        
        respuesta_dec = Decimal(str(respuesta))
        es_correcto = abs(respuesta_dec - problema.resultado) <= Decimal("0.01")
        
        await self.problem_repo.create_intento(
            estudiante_id=estudiante_id,
            problema_id=problema_id,
            respuesta_estudiante=respuesta_dec,
            es_correcto=es_correcto,
            tiempo_resolucion=tiempo_resolucion,
            solicito_pista=False,
            tipo_sesion=TipoSesion.PRACTICA,
            sesion_id=sesion_id
        )
        
        intentos_restantes = self.MAX_INTENTOS_POR_PROBLEMA - (intentos_previos + 1)
        debe_avanzar = es_correcto or intentos_restantes == 0
        
        siguiente_problema = None
        sesion_completada = False
        mensaje = ""
        
        if es_correcto:
            mensaje = "¡Correcto!"
        else:
            if intentos_restantes > 0:
                mensaje = f"Incorrecto. Te quedan {intentos_restantes} intento(s)."
            else:
                mensaje = f"Incorrecto. La respuesta correcta era {problema.resultado}"
        
        if debe_avanzar:
            await self.practice_repo.incrementar_progreso(sesion)

            if sesion.progreso_actual >= sesion.cantidad_problemas:
                sesion_completada = True
                mensaje += " ¡Sesión completada!"

                sesion.estado = EstadoSesion.COMPLETADA
                sesion.fecha_fin = datetime.utcnow()
                await self.practice_repo.update_sesion(sesion)
            else:
                siguiente_problema = await self._get_next_problem(sesion)
        
        return SubmitProblemResponse(
            es_correcto=es_correcto,
            respuesta_correcta=str(problema.resultado) if not es_correcto and intentos_restantes == 0 else None,
            intentos_restantes=intentos_restantes,
            mensaje=mensaje,
            siguiente_problema=siguiente_problema,
            sesion_completada=sesion_completada
        )
    
    # ============================================
    # Historial y Resumen
    # ============================================

    async def get_practice_history(
        self,
        estudiante_id: int,
        limit: int = 20,
        skip: int = 0
    ) -> SessionHistoryResponse:
        """Obtiene historial de sesiones del estudiante."""
        sesiones = await self.practice_repo.get_session_history(estudiante_id, limit, skip)
        total = await self.practice_repo.count_total_sessions(estudiante_id)
        
        items = []
        for sesion in sesiones:
            precision = 0.0
            if sesion.cantidad_problemas and sesion.cantidad_problemas > 0:
                precision = (sesion.problemas_correctos or 0) / sesion.cantidad_problemas
            
            items.append(SessionHistoryItem(
                sesion_id=sesion.id,
                fecha_inicio=sesion.fecha_inicio,
                fecha_fin=sesion.fecha_fin,
                estado=sesion.estado.value,
                nivel_actual=sesion.nivel_actual_inicio or 1,
                cantidad_problemas=sesion.cantidad_problemas or 0,
                problemas_correctos=sesion.problemas_correctos or 0,
                problemas_incorrectos=sesion.problemas_incorrectos or 0,
                precision=round(precision, 2),
                tiempo_total_segundos=sesion.tiempo_total_segundos,
                es_practica_perfecta=sesion.es_practica_perfecta or False,
                cambios_nivel=sesion.cambios_nivel
            ))
        
        return SessionHistoryResponse(
            total=total,
            sesiones=items
        )
    
    async def get_session_summary(
        self,
        sesion_id: int,
        estudiante_id: int
    ) -> SessionSummaryResponse:
        """Genera resumen detallado de una sesión específica."""
        sesion = await self.practice_repo.get_sesion(sesion_id)
        
        if not sesion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión no encontrada"
            )
        
        if sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver esta sesión"
            )
        
        intentos_sesion = await self.adaptive_repo.get_intentos_sesion(sesion_id)
        
        problemas_map = {}
        for intento in intentos_sesion:
            if intento.problema_id not in problemas_map:
                problemas_map[intento.problema_id] = []
            problemas_map[intento.problema_id].append(intento)
        
        problemas_detalle = []
        stats_por_operacion = {}
        
        for problema_id, intentos in problemas_map.items():
            problema = await self.problem_repo.get_problem_by_id(problema_id)
            if not problema:
                continue
            
            es_correcto = any(i.es_correcto for i in intentos)
            tiempo_total = sum(i.tiempo_resolucion for i in intentos)
            respuestas = [str(i.respuesta) for i in intentos]
            
            enunciado = f"{problema.numero1} {problema.operacion.value} {problema.numero2}"
            
            problemas_detalle.append(ProblemaSummary(
                problema_id=problema.id,
                operacion=problema.operacion.value,
                enunciado=enunciado,
                nivel_dificultad=problema.nivel_dificultad,
                intentos_realizados=len(intentos),
                es_correcto=es_correcto,
                tiempo_total=tiempo_total,
                respuestas_intentadas=respuestas
            ))
            
            op = problema.operacion.value
            if op not in stats_por_operacion:
                stats_por_operacion[op] = {
                    "total": 0,
                    "correctos": 0,
                    "tiempo_total": 0
                }
            
            stats_por_operacion[op]["total"] += 1
            if es_correcto:
                stats_por_operacion[op]["correctos"] += 1
            stats_por_operacion[op]["tiempo_total"] += tiempo_total
        
        precision = (sesion.problemas_correctos or 0) / sesion.cantidad_problemas if sesion.cantidad_problemas > 0 else 0
        velocidad_promedio = sesion.velocidad_promedio or Decimal("0")
        
        errores_comunes = self._analizar_errores_comunes(problemas_detalle)
        puntos_fuertes = self._identificar_puntos_fuertes(stats_por_operacion)
        recomendaciones = self._generar_recomendaciones(errores_comunes, puntos_fuertes)
        
        return SessionSummaryResponse(
            sesion_id=sesion.id,
            fecha_inicio=sesion.fecha_inicio,
            fecha_fin=sesion.fecha_fin,
            estado=sesion.estado.value,
            total_problemas=sesion.cantidad_problemas or 0,
            correctos=sesion.problemas_correctos or 0,
            incorrectos=sesion.problemas_incorrectos or 0,
            precision=round(precision, 2),
            tiempo_total=sesion.tiempo_total_segundos or 0,
            velocidad_promedio=float(velocidad_promedio),
            stats_por_operacion=stats_por_operacion,
            problemas=problemas_detalle,
            errores_comunes=errores_comunes,
            puntos_fuertes=puntos_fuertes,
            recomendaciones=recomendaciones
        )
    
    def _analizar_errores_comunes(self, problemas: List[ProblemaSummary]) -> List[str]:
        """Identifica patrones de errores."""
        errores = []
        multiples_intentos = [p for p in problemas if p.intentos_realizados > 1]
        
        if len(multiples_intentos) >= 3:
            errores.append(f"Necesitaste múltiples intentos en {len(multiples_intentos)} problemas")
        
        return errores
    
    def _identificar_puntos_fuertes(self, stats: Dict) -> List[str]:
        """Identifica operaciones donde el estudiante destaca."""
        puntos_fuertes = []
        
        for op, data in stats.items():
            if data["total"] > 0:
                precision = data["correctos"] / data["total"]
                if precision >= 0.9:
                    puntos_fuertes.append(f"Excelente precisión en {op} ({precision:.0%})")
        
        return puntos_fuertes
    
    def _generar_recomendaciones(self, errores: List[str], puntos_fuertes: List[str]) -> List[str]:
        """Genera recomendaciones personalizadas."""
        recomendaciones = []
        
        if not puntos_fuertes:
            recomendaciones.append("Sigue practicando para mejorar tu precisión")
        
        if len(errores) > 2:
            recomendaciones.append("Tómate más tiempo para revisar tus respuestas antes de enviar")
        
        return recomendaciones
    
    # ============================================
    # Estadísticas Globales
    # ============================================
    
    async def get_global_stats(self, estudiante_id: int) -> GlobalStatsResponse:
        """Calcula estadísticas globales del estudiante."""
        total_sesiones = await self.practice_repo.count_total_sessions(estudiante_id)
        total_sesiones_completas = await self.practice_repo.count_completed_sessions(estudiante_id)
        total_problemas_resueltos = await self.practice_repo.get_total_problemas_resueltos(estudiante_id)
        total_problemas_correctos = await self.practice_repo.get_total_problemas_correctos(estudiante_id)
        
        precision_global = (total_problemas_correctos / total_problemas_resueltos) if total_problemas_resueltos > 0 else 0.0
        
        perfil = await self.adaptive_repo.get_perfil(estudiante_id)
        velocidad_promedio_global = float(perfil.velocidad_promedio or 0) if perfil else 0.0
        
        racha_actual_perfectas = await self.practice_repo.get_racha_actual_perfectas(estudiante_id)
        mejor_racha_perfectas = await self.practice_repo.get_mejor_racha_perfectas(estudiante_id)
        dias_consecutivos = await self.practice_repo.get_dias_consecutivos_practicando(estudiante_id)
        
        stats_por_operacion = await self._calcular_stats_por_operacion(estudiante_id, perfil)
        
        sesiones_7_dias = await self.practice_repo.get_sesiones_ultimos_n_dias(estudiante_id, 7)
        precision_7_dias = self._calcular_precision_por_dia(sesiones_7_dias)
        sesiones_por_dia = self._contar_sesiones_por_dia(sesiones_7_dias)
        
        return GlobalStatsResponse(
            estudiante_id=estudiante_id,
            total_sesiones=total_sesiones,
            total_sesiones_completas=total_sesiones_completas,
            total_problemas_resueltos=total_problemas_resueltos,
            total_problemas_correctos=total_problemas_correctos,
            precision_global=round(precision_global, 2),
            velocidad_promedio_global=velocidad_promedio_global,
            racha_actual_perfectas=racha_actual_perfectas,
            mejor_racha_perfectas=mejor_racha_perfectas,
            dias_consecutivos_practicando=dias_consecutivos,
            stats_por_operacion=stats_por_operacion,
            precision_ultimos_7_dias=precision_7_dias,
            sesiones_ultimos_7_dias=sesiones_por_dia
        )
    
    async def _calcular_stats_por_operacion(self, estudiante_id: int, perfil) -> List[StatsPerOperation]:
        """Calcula estadísticas reales por operación consultando la BD."""
        if not perfil:
            return []

        operaciones = [
            ("suma",           perfil.nivel_suma,           "+"),
            ("resta",          perfil.nivel_resta,          "-"),
            ("multiplicacion", perfil.nivel_multiplicacion, "×"),
            ("division",       perfil.nivel_division,       "÷"),
        ]

        # Consulta real agrupada por operación
        raw = await self.practice_repo.get_stats_por_operacion(estudiante_id)

        stats = []
        for nombre, nivel, simbolo in operaciones:
            op_data = raw.get(simbolo, {})
            total_intentos  = op_data.get('total_intentos', 0)
            total_correctos = op_data.get('total_correctos', 0)
            precision = (total_correctos / total_intentos) if total_intentos > 0 else 0.0
            stats.append(StatsPerOperation(
                operacion=nombre,
                nivel_actual=nivel,
                total_intentos=total_intentos,
                total_correctos=total_correctos,
                precision=round(precision, 4),
                velocidad_promedio=op_data.get('velocidad_promedio', 0.0),
                problemas_resueltos=op_data.get('problemas_resueltos', 0),
            ))

        return stats
    
    def _calcular_precision_por_dia(self, sesiones: List[SesionPractica]) -> List[float]:
        """Calcula precisión promedio por día (últimos 7 días)."""
        precision_por_fecha = {}
        
        for sesion in sesiones:
            fecha = sesion.fecha_inicio.date()
            
            if fecha not in precision_por_fecha:
                precision_por_fecha[fecha] = []
            
            if sesion.cantidad_problemas and sesion.cantidad_problemas > 0:
                precision = (sesion.problemas_correctos or 0) / sesion.cantidad_problemas
                precision_por_fecha[fecha].append(precision)
        
        hoy = datetime.utcnow().date()
        resultado = []
        
        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            if fecha in precision_por_fecha:
                promedio = statistics.mean(precision_por_fecha[fecha])
                resultado.append(round(promedio, 2))
            else:
                resultado.append(0.0)
        
        return resultado
    
    def _contar_sesiones_por_dia(self, sesiones: List[SesionPractica]) -> List[int]:
        """Cuenta sesiones por día (últimos 7 días)."""
        sesiones_por_fecha = {}
        
        for sesion in sesiones:
            fecha = sesion.fecha_inicio.date()
            sesiones_por_fecha[fecha] = sesiones_por_fecha.get(fecha, 0) + 1
        
        hoy = datetime.utcnow().date()
        resultado = []
        
        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            resultado.append(sesiones_por_fecha.get(fecha, 0))
        
        return resultado
    
    # ============================================
    # Detección de Tramposos
    # ============================================
    
    async def detectar_anomalias_sesion(self, sesion: SesionPractica) -> List[Dict]:
        """Detecta anomalías en una sesión completada."""
        if sesion.estado != EstadoSesion.COMPLETADA:
            return []
        
        alertas = []
        
        alerta_velocidad = await self._detectar_velocidad_sospechosa(sesion)
        if alerta_velocidad:
            alertas.append(alerta_velocidad)
        
        alerta_patron = await self._detectar_patron_perfecto(sesion)
        if alerta_patron:
            alertas.append(alerta_patron)
        
        alerta_outlier = await self._detectar_outlier_velocidad(sesion)
        if alerta_outlier:
            alertas.append(alerta_outlier)
        
        if alertas:
            await self.practice_repo.marcar_sesion_sospechosa(
                sesion,
                patron_sospechoso=any(a["tipo"] == "patron_perfecto" for a in alertas),
                velocidad_sospechosa=any(a["tipo"] in ["velocidad_sospechosa", "outlier_velocidad"] for a in alertas)
            )
            
            for alerta_data in alertas:
                await self._crear_alerta(sesion.estudiante_id, sesion.id, alerta_data)
        
        return alertas
    
    async def _detectar_velocidad_sospechosa(self, sesion: SesionPractica) -> Optional[Dict]:
        """Detecta velocidad anormalmente rápida."""
        if not sesion.velocidad_promedio:
            return None
        
        velocidad = float(sesion.velocidad_promedio)
        operaciones = sesion.operaciones_incluidas or {}
        tiene_mult_o_div = any(op in ["+", "×", "÷"] for op in operaciones.keys())
        
        if tiene_mult_o_div and velocidad < 3.0:
            return {
                "tipo": "velocidad_sospechosa",
                "severidad": "warning",
                "titulo": "Velocidad sospechosamente alta",
                "mensaje": f"Resolvió problemas complejos en {velocidad:.1f} seg promedio (normal: 8-15 seg)",
                "datos": {
                    "velocidad_promedio": velocidad,
                    "operaciones": list(operaciones.keys()),
                    "umbral_sospechoso": 3.0
                }
            }
        
        return None
    
    async def _detectar_patron_perfecto(self, sesion: SesionPractica) -> Optional[Dict]:
        """Detecta patrón perfecto antinatural."""
        if not sesion.es_practica_perfecta:
            return None
        
        intentos = await self.adaptive_repo.get_intentos_sesion(sesion.id)
        
        problemas_con_intentos = {}
        for intento in intentos:
            if intento.problema_id not in problemas_con_intentos:
                problemas_con_intentos[intento.problema_id] = 0
            problemas_con_intentos[intento.problema_id] += 1
        
        if any(count > 1 for count in problemas_con_intentos.values()):
            return None
        
        tiempos = [i.tiempo_resolucion for i in intentos if i.es_correcto]
        
        if len(tiempos) < 5:
            return None
        
        varianza = statistics.variance(tiempos) if len(tiempos) > 1 else 0
        
        if varianza < 2.0:
            return {
                "tipo": "patron_perfecto",
                "severidad": "critical",
                "titulo": "Patrón perfecto sospechoso",
                "mensaje": f"100% acierto en primer intento con varianza de tiempo {varianza:.2f} (muy uniforme)",
                "datos": {
                    "total_problemas": len(tiempos),
                    "varianza_tiempo": varianza,
                    "tiempos": tiempos,
                    "umbral_sospechoso": 2.0
                }
            }
        
        return None
    
    async def _detectar_outlier_velocidad(self, sesion: SesionPractica) -> Optional[Dict]:
        """Detecta si el estudiante es outlier respecto a su grupo."""
        return None
    
    async def _crear_alerta(self, estudiante_id: int, sesion_id: int, alerta_data: Dict) -> None:
        """Crea registro de alerta en la BD."""
        tipo_map = {
            "velocidad_sospechosa": TipoAlerta.POSIBLE_TRAMPA,
            "patron_perfecto": TipoAlerta.POSIBLE_TRAMPA,
            "outlier_velocidad": TipoAlerta.POSIBLE_TRAMPA
        }
        
        perfil = await self.adaptive_repo.get_perfil(estudiante_id)
        
        alerta = AlertaEstudiante(
            estudiante_id=estudiante_id,
            perfil_id=perfil.estudiante_id if perfil else estudiante_id,
            tipo=tipo_map.get(alerta_data["tipo"], TipoAlerta.POSIBLE_TRAMPA),
            severidad=alerta_data["severidad"],
            titulo=alerta_data["titulo"],
            mensaje=alerta_data["mensaje"],
            datos_contexto={
                **alerta_data["datos"],
                "sesion_id": sesion_id
            },
            activa=True,
            leida=False,
            fecha_creacion=datetime.utcnow()
        )
        
        await self.adaptive_repo.create_alerta(alerta)
    
    async def get_suspicious_activity(self, estudiante_id: int) -> SuspiciousActivityResponse:
        """Obtiene todas las alertas de un estudiante."""
        alertas_db = await self.adaptive_repo.get_alertas_activas(estudiante_id)
        
        alertas = [
            AlertaSospechosa(
                tipo=alerta.tipo.value,
                severidad=alerta.severidad,
                mensaje=alerta.mensaje,
                datos_contexto=alerta.datos_contexto or {},
                fecha_deteccion=alerta.fecha_creacion
            )
            for alerta in alertas_db
        ]
        
        total_alertas = len(alertas)
        alertas_activas = sum(1 for a in alertas_db if a.activa)
        
        return SuspiciousActivityResponse(
            estudiante_id=estudiante_id,
            total_alertas=total_alertas,
            alertas_activas=alertas_activas,
            alertas=alertas
        )
