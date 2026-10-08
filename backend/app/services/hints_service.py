"""
Service para gestión de pistas.

Niveles 1 y 2: pistas de estrategia escritas en el código, por operación (gratis).
Nivel 3: pista generada con el LLM a partir de los intentos del estudiante (10 puntos).
El profesor puede deshabilitar niveles por grupo (`pistas_habilitadas`).
"""

import time
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, status

from app.models.hints import NivelPista
from app.models.problem import Operacion, Problema
from app.repositories.adaptive_repository import AdaptiveRepository
from app.repositories.gamification_repository import GamificationRepository
from app.repositories.hints_repository import HintsRepository
from app.schemas.hints import PistaResponse
from app.services.deteccion_errores_service import DeteccionErroresService
from app.services.llm_service import LLMPrompts, LLMService

# Pistas de estrategia (niveles 1 y 2) por operación.
PISTAS_ESTRATEGIA: Dict[Operacion, Dict[int, str]] = {
    Operacion.SUMA: {
        1: "Escribe un número debajo del otro, alineando unidades con unidades, décimas con décimas "
           "y centésimas con centésimas. Después suma de derecha a izquierda.",
        2: "Empieza por la columna de la derecha y suma sus dígitos. Si el resultado pasa de 9, "
           "escribe solo la unidad y lleva 1 a la columna de la izquierda. Pon el punto decimal "
           "justo debajo de los puntos de los sumandos.",
    },
    Operacion.RESTA: {
        1: "Pon el número más grande arriba y alinea las columnas por el punto decimal. "
           "Después resta de derecha a izquierda.",
        2: "En cada columna resta el dígito de abajo al de arriba. Si el de arriba es menor, "
           "pídele 1 a la columna de la izquierda: esa unidad vale 10 en tu columna. "
           "Pon el punto decimal justo debajo de los otros puntos.",
    },
    Operacion.MULTIPLICACION: {
        1: "Multiplica como si fueran números enteros, sin mirar el punto. "
           "El punto decimal lo colocas al final.",
        2: "Multiplica el número de arriba por cada dígito del de abajo, de derecha a izquierda, "
           "corriendo cada producto un lugar a la izquierda, y suma los productos. "
           "Al final cuenta cuántos decimales tienen los dos números juntos y coloca el punto "
           "contando esa cantidad desde la derecha.",
    },
    Operacion.DIVISION: {
        1: "Si el divisor tiene punto decimal, multiplica el divisor y el dividendo por 10, 100... "
           "hasta que el divisor sea entero. Después divide.",
        2: "Divide paso a paso: ¿cuántas veces cabe el divisor en las primeras cifras? Escribe esa "
           "cifra en el cociente, multiplica, resta y baja la siguiente cifra. Cuando llegues al "
           "punto decimal del dividendo, pon el punto en el cociente.",
    },
}
AVISO_DECIMALES_SUMA_RESTA = " Si a un número le faltan cifras decimales, complétalo con ceros."


class HintsService:
    """Service para gestión de pistas."""

    # Costo de pista nivel 3
    COSTO_PISTA_NIVEL_3 = 10

    def __init__(
        self,
        hints_repo: HintsRepository,
        gamification_repo: GamificationRepository,
        adaptive_repo: AdaptiveRepository,
        llm_service: LLMService
    ):
        self.hints_repo = hints_repo
        self.gamification_repo = gamification_repo
        self.adaptive_repo = adaptive_repo
        self.llm_service = llm_service

    async def _niveles_habilitados(self, estudiante_id: int) -> Dict[int, bool]:
        """Niveles de pista permitidos por la configuración activa del grupo del estudiante."""
        config = await self.adaptive_repo.get_config_practica_estudiante(estudiante_id)
        habilitadas = (config.pistas_habilitadas if config else None) or {}
        return {n: bool(habilitadas.get(f"nivel_{n}", True)) for n in (1, 2, 3)}

    async def solicitar_pista(
        self,
        estudiante_id: int,
        sesion_id: int,
        problema_id: int,
        nivel_pista: int
    ) -> PistaResponse:
        """
        Solicita una pista para un problema.

        Nivel 1-2: gratis, estrategia por operación.
        Nivel 3: 10 puntos (solo si la pista se genera), generada con LLM.
        """
        if nivel_pista not in [1, 2, 3]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nivel de pista debe ser 1, 2 o 3"
            )

        nivel_enum = NivelPista(nivel_pista)

        # La sesión debe ser del estudiante y el problema debe pertenecer a ella
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta sesión"
            )
        if problema_id not in (sesion.problemas_ids or []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El problema no pertenece a esta sesión"
            )

        # El profesor puede deshabilitar niveles de pista para el grupo
        if not (await self._niveles_habilitados(estudiante_id))[nivel_pista]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu profesor deshabilitó la pista nivel {nivel_pista}"
            )

        # No repetir la misma pista en el mismo problema
        pistas_usadas = await self.hints_repo.get_pistas_usadas_sesion(sesion_id, problema_id)
        if nivel_enum in {p.nivel_pista for p in pistas_usadas}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya solicitaste la pista nivel {nivel_pista} para este problema"
            )

        problema = await self.adaptive_repo.get_problema(problema_id)
        if not problema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problema no encontrado"
            )

        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)
        puntos_gastados = 0

        # Nivel 3 requiere saldo suficiente (el cobro ocurre solo si la pista se genera)
        if nivel_pista == 3 and saldo < self.COSTO_PISTA_NIVEL_3:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Necesitas {self.COSTO_PISTA_NIVEL_3} puntos para esta pista (tienes {saldo})"
            )

        if nivel_pista in [1, 2]:
            contenido = self._pista_de_estrategia(problema, nivel_pista)
            generada_llm = False
        else:
            # Si el LLM falla se entrega una pista genérica y NO se cobra: el
            # estudiante no recibió lo que pagaría.
            contenido, generada_llm = await self._generar_pista_nivel_3(
                problema, estudiante_id, sesion_id
            )
            if generada_llm:
                await self.gamification_repo.gastar_puntos(
                    estudiante_id=estudiante_id,
                    cantidad=self.COSTO_PISTA_NIVEL_3,
                    concepto=f"Pista nivel 3 - Problema #{problema_id}"
                )
                puntos_gastados = self.COSTO_PISTA_NIVEL_3
                saldo -= self.COSTO_PISTA_NIVEL_3

        await self.hints_repo.registrar_uso_pista(
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

    def _pista_de_estrategia(self, problema: Problema, nivel_pista: int) -> str:
        """Pista de nivel 1-2: estrategia de la operación (con aviso si hay decimales)."""
        texto = PISTAS_ESTRATEGIA[problema.operacion][nivel_pista]
        tiene_decimales = (
            problema.numero1 != problema.numero1.to_integral_value()
            or problema.numero2 != problema.numero2.to_integral_value()
        )
        if (
            nivel_pista == 1
            and tiene_decimales
            and problema.operacion in (Operacion.SUMA, Operacion.RESTA)
        ):
            texto += AVISO_DECIMALES_SUMA_RESTA
        return texto

    async def _generar_pista_nivel_3(
        self,
        problema: Problema,
        estudiante_id: int,
        sesion_id: int
    ) -> Tuple[str, bool]:
        """
        Genera la pista nivel 3 con el LLM (V3).

        El prompt incluye las respuestas incorrectas previas del estudiante en este
        problema y el tipo de error detectado en la última.

        Returns:
            (texto, generada_llm). Si el LLM falla devuelve un texto genérico y False.
        """
        intentos = await self.adaptive_repo.get_intentos_problema(estudiante_id, problema.id)
        incorrectos = [i for i in intentos if not i.es_correcto]
        respuestas_previas = [float(i.respuesta_estudiante) for i in incorrectos][-3:]
        respuesta_incorrecta = respuestas_previas[-1] if respuestas_previas else None

        tipo_error: Optional[str] = None
        if incorrectos:
            tipo = DeteccionErroresService.detectar_tipo_error(problema, incorrectos[-1].respuesta_estudiante)
            tipo_error = DeteccionErroresService.obtener_descripcion_error(tipo)

        prompt = LLMPrompts.generar_pista_nivel_3(
            operacion=problema.operacion.value,
            operando1=float(problema.numero1),
            operando2=float(problema.numero2),
            resultado=float(problema.resultado),
            respuesta_incorrecta=respuesta_incorrecta,
            respuestas_previas=respuestas_previas,
            tipo_error=tipo_error,
        )

        inicio = time.time()
        try:
            contenido = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=150
            )
            await self.hints_repo.registrar_generacion_llm(
                tipo="pista_nivel_3",
                prompt_usado=prompt,
                respuesta_llm=contenido,
                modelo=self.llm_service.model_v3,
                problema_id=problema.id,
                tokens_usados=self.llm_service.ultimo_total_tokens,
                tiempo_generacion_ms=int((time.time() - inicio) * 1000),
                exitoso=True
            )
            return contenido.strip(), True
        except Exception as e:
            await self.hints_repo.registrar_generacion_llm(
                tipo="pista_nivel_3",
                prompt_usado=prompt,
                respuesta_llm="",
                modelo=self.llm_service.model_v3,
                problema_id=problema.id,
                exitoso=False,
                error=str(e)
            )
            return (
                "Piensa en cómo descomponer el problema en pasos más pequeños. "
                "Revisa tus cálculos cuidadosamente.",
                False,
            )

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
                "niveles_disponibles": [1, 2, 3],   # no usados y habilitados por el profesor
                "niveles_usados": [1],
                "puede_pagar_nivel_3": True,
                "costo_nivel_3": 10,
                "saldo_actual": 120
            }
        """
        sesion = await self.adaptive_repo.get_sesion(sesion_id)
        if not sesion or sesion.estudiante_id != estudiante_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta sesión"
            )

        pistas_usadas = await self.hints_repo.get_pistas_usadas_sesion(sesion_id, problema_id)
        niveles_usados = [p.nivel_pista.value for p in pistas_usadas]
        habilitados = await self._niveles_habilitados(estudiante_id)
        niveles_disponibles = [n for n in (1, 2, 3) if n not in niveles_usados and habilitados[n]]

        saldo = await self.gamification_repo.get_saldo_puntos(estudiante_id)

        return {
            "niveles_disponibles": niveles_disponibles,
            "niveles_usados": niveles_usados,
            "puede_pagar_nivel_3": saldo >= self.COSTO_PISTA_NIVEL_3,
            "costo_nivel_3": self.COSTO_PISTA_NIVEL_3,
            "saldo_actual": saldo
        }
