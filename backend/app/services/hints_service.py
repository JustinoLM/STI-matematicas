"""
Service para gestión de pistas.

Maneja pistas pre-escritas (nivel 1-2) y generadas con LLM (nivel 3).
"""

import time
from typing import Optional
from fastapi import HTTPException, status

from app.repositories.hints_videos_repository import HintsVideosRepository
from app.repositories.gamification_repository import GamificationRepository
from app.repositories.adaptive_repository import AdaptiveRepository
from app.services.llm_service import LLMService, LLMPrompts
from app.models.hints_videos import NivelPista, TipoError
from app.models.problem import Problema
from app.schemas.hints_videos import PistaResponse


class HintsService:
    """Service para gestión de pistas."""
    
    # Costo de pista nivel 3
    COSTO_PISTA_NIVEL_3 = 10
    
    def __init__(
        self,
        hints_videos_repo: HintsVideosRepository,
        gamification_repo: GamificationRepository,
        adaptive_repo: AdaptiveRepository,
        llm_service: LLMService
    ):
        self.hints_videos_repo = hints_videos_repo
        self.gamification_repo = gamification_repo
        self.adaptive_repo = adaptive_repo
        self.llm_service = llm_service
    
    async def solicitar_pista(
        self,
        estudiante_id: int,
        sesion_id: int,
        problema_id: int,
        nivel_pista: int
    ) -> PistaResponse:
        """
        Solicita una pista para un problema.
        
        Nivel 1-2: Gratis, pre-escritas
        Nivel 3: 10 puntos, generada con LLM
        """
        # Validar nivel
        if nivel_pista not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nivel de pista debe ser 1, 2 o 3"
            )
        
        nivel_enum = NivelPista(nivel_pista)
        
        # Verificar que la sesión pertenece al estudiante
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta sesión"
            )
        
        # Verificar que no ha pedido esta pista antes
        pistas_usadas = await self.hints_videos_repo.get_pistas_usadas_sesion(
            sesion_id,
            problema_id
        )
        
        niveles_usados = {p.nivel_pista for p in pistas_usadas}
        
        if nivel_enum in niveles_usados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya solicitaste la pista nivel {nivel_pista} para este problema"
            )
        
        # Obtener problema
        problema = await self.adaptive_repo.get_problema(problema_id)
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problema no encontrado"
            )
        
        # Obtener saldo actual
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        puntos_gastados = 0
        
        # Nivel 3 requiere pago
        if nivel_pista == 3:
            if saldo < self.COSTO_PISTA_NIVEL_3:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Necesitas {self.COSTO_PISTA_NIVEL_3} puntos para esta pista (tienes {saldo})"
                )
            
            # Gastar puntos
            await self.gamification_repo.gastar_puntos(
                estudiante_id=estudiante_id,
                cantidad=self.COSTO_PISTA_NIVEL_3,
                concepto=f"Pista nivel 3 - Problema #{problema_id}"
            )
            
            puntos_gastados = self.COSTO_PISTA_NIVEL_3
            saldo -= self.COSTO_PISTA_NIVEL_3
        
        # Obtener contenido de la pista
        if nivel_pista in [1, 2]:
            contenido = await self._obtener_pista_preescrita(problema, nivel_enum)
            generada_llm = False
        else:
            # Nivel 3: Generar con LLM
            contenido = await self._generar_pista_nivel_3(problema, estudiante_id, sesion_id)
            generada_llm = True
        
        # Registrar uso
        await self.hints_videos_repo.registrar_uso_pista(
            estudiante_id=estudiante_id,
            sesion_id=sesion_id,
            problema_id=problema_id,
            nivel_pista=nivel_enum,
            puntos_gastados=puntos_gastados,
            generada_llm=generada_llm,
            contenido_pista=contenido if generada_llm else None
        )
        
        return PistaResponse(
            nivel_pista=nivel_pista,
            contenido=contenido,
            puntos_gastados=puntos_gastados,
            saldo_nuevo=saldo,
            generada_llm=generada_llm
        )
    
    async def _obtener_pista_preescrita(
        self,
        problema: Problema,
        nivel_pista: NivelPista
    ) -> str:
        """Obtiene pista pre-escrita de la BD."""
        tiene_decimales = (
            '.' in str(problema.operando1) or 
            '.' in str(problema.operando2)
        )
        
        pista = await self.hints_videos_repo.get_pista_generica(
            operacion=problema.operacion,
            tiene_decimales=tiene_decimales,
            nivel_pista=nivel_pista
        )
        
        if not pista:
            # Fallback genérico
            if nivel_pista == NivelPista.NIVEL_1:
                return "Recuerda los pasos básicos de esta operación. Tómate tu tiempo y verifica cada paso."
            else:
                return "Descompón el problema en pasos pequeños. Primero identifica qué operación necesitas hacer."
        
        return pista.contenido
    
    async def _generar_pista_nivel_3(
        self,
        problema: Problema,
        estudiante_id: int,
        sesion_id: int
    ) -> str:
        """Genera pista nivel 3 con LLM."""
        
        # Obtener último intento del estudiante
        intentos = await self.adaptive_repo.get_intentos_problema(
            estudiante_id,
            problema.id
        )
        
        respuesta_incorrecta = None
        if intentos:
            ultimo_intento = intentos[-1]
            respuesta_incorrecta = float(ultimo_intento.respuesta_estudiante)
        
        # Construir prompt
        operacion_map = {
            "suma": "+",
            "resta": "-",
            "multiplicacion": "×",
            "division": "÷"
        }
        
        operacion_simbolo = operacion_map.get(problema.operacion.value, problema.operacion.value)
        
        prompt = LLMPrompts.generar_pista_nivel_3(
            operacion=operacion_simbolo,
            operando1=float(problema.operando1),
            operando2=float(problema.operando2),
            resultado=float(problema.resultado),
            respuesta_incorrecta=respuesta_incorrecta or 0.0
        )
        
        # Generar con LLM
        inicio = time.time()
        
        try:
            contenido = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=150
            )
            
            tiempo_ms = int((time.time() - inicio) * 1000)
            
            # Registrar generación
            await self.hints_videos_repo.registrar_generacion_llm(
                tipo="pista_nivel_3",
                prompt_usado=prompt,
                respuesta_llm=contenido,
                modelo=self.llm_service.model_v3,
                problema_id=problema.id,
                tiempo_generacion_ms=tiempo_ms,
                exitoso=True
            )
            
            return contenido.strip()
            
        except Exception as e:
            # Registrar error
            await self.hints_videos_repo.registrar_generacion_llm(
                tipo="pista_nivel_3",
                prompt_usado=prompt,
                respuesta_llm="",
                modelo=self.llm_service.model_v3,
                problema_id=problema.id,
                exitoso=False,
                error=str(e)
            )
            
            # Fallback genérico
            return "Piensa en cómo descomponer el problema en pasos más pequeños. Revisa tus cálculos cuidadosamente."
    
    async def get_pistas_disponibles(
        self,
        estudiante_id: int,
        sesion_id: int,
        problema_id: int
    ) -> dict:
        """
        Retorna qué pistas están disponibles para solicitar.
        
        Returns:
            {
                "niveles_disponibles": [1, 2, 3],
                "niveles_usados": [1],
                "puede_pagar_nivel_3": True,
                "costo_nivel_3": 10
            }
        """
        # Obtener pistas ya usadas
        pistas_usadas = await self.hints_videos_repo.get_pistas_usadas_sesion(
            sesion_id,
            problema_id
        )
        
        niveles_usados = [p.nivel_pista.value for p in pistas_usadas]
        niveles_disponibles = [n for n in [1, 2, 3] if n not in niveles_usados]
        
        # Verificar si puede pagar nivel 3
        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        puede_pagar_nivel_3 = saldo >= self.COSTO_PISTA_NIVEL_3
        
        return {
            "niveles_disponibles": niveles_disponibles,
            "niveles_usados": niveles_usados,
            "puede_pagar_nivel_3": puede_pagar_nivel_3,
            "costo_nivel_3": self.COSTO_PISTA_NIVEL_3,
            "saldo_actual": saldo
        }
