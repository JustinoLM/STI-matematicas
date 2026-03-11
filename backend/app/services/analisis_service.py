"""
Service para análisis post-práctica con DeepSeek R1.

Consulta estadísticas de la sesión y genera un análisis pedagógico
personalizado usando el modelo de razonamiento R1.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.adaptive import SesionPractica, PerfilEstudiante
from app.models.user import Estudiante
from app.services.llm_service import LLMService, LLMPrompts


class AnalisisService:
    """Service para generar análisis post-práctica con R1."""

    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm = llm_service

    async def generar_analisis(
        self, sesion_id: int, estudiante: Estudiante
    ) -> tuple[str, bool]:
        """
        Genera un análisis pedagógico de la sesión completada.

        Returns:
            (texto, generada_llm) — generada_llm=False si se usó fallback.
        """
        # ── 1. Obtener sesión ────────────────────────────────────────────────
        result = await self.db.execute(
            select(SesionPractica).where(
                and_(
                    SesionPractica.id == sesion_id,
                    SesionPractica.estudiante_id == estudiante.id,
                )
            )
        )
        sesion = result.scalar_one_or_none()
        if sesion is None:
            return self._fallback(0.0), False

        # ── 2. Extraer estadísticas de la sesión ─────────────────────────────
        total_problemas: int = sesion.cantidad_problemas or 0
        total_correctos: int = sesion.problemas_correctos or 0
        precision: float = (
            total_correctos / total_problemas if total_problemas > 0 else 0.0
        )
        tiempo_promedio: float = float(sesion.velocidad_promedio or 0.0)

        # Operación principal (la que más problemas tiene en la sesión)
        operaciones_incluidas: dict = sesion.operaciones_incluidas or {}
        if operaciones_incluidas:
            operacion_principal = max(
                operaciones_incluidas, key=lambda k: operaciones_incluidas[k]
            )
        else:
            operacion_principal = "suma"

        # ── 3. Nivel del estudiante ──────────────────────────────────────────
        nivel = sesion.nivel_actual_inicio or 1

        # ── 4. Género del estudiante ─────────────────────────────────────────
        genero_val = getattr(estudiante, "genero", None)
        genero = genero_val.value if hasattr(genero_val, "value") else str(genero_val or "masculino")

        # ── 5. Construir prompt y llamar R1 ──────────────────────────────────
        prompt = LLMPrompts.analisis_post_practica(
            nombre=estudiante.nombre_completo,
            genero=genero,
            operacion=_operacion_label(operacion_principal),
            nivel=nivel,
            total_problemas=total_problemas,
            total_correctos=total_correctos,
            precision=precision,
            tiempo_promedio_seg=tiempo_promedio,
            pasos_intermedios_correctos=0,
            pasos_intermedios_total=0,
        )

        try:
            texto = await self.llm.generate(
                prompt=prompt,
                use_reasoning=True,
                max_tokens=300,
            )
            return texto.strip(), True
        except Exception:
            return self._fallback(precision), False

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback(precision: float) -> str:
        if precision >= 0.8:
            return "¡Excelente sesión! Tus resultados muestran un gran dominio. Sigue practicando para llegar al siguiente nivel."
        elif precision >= 0.6:
            return "Buen trabajo en esta sesión. Cada práctica te ayuda a mejorar. ¡Sigue adelante!"
        else:
            return "¡Gracias por practicar! Los errores son parte del aprendizaje. Sigue intentándolo y verás cómo mejoras."


def _operacion_label(key: str) -> str:
    """Convierte clave de operación a etiqueta legible."""
    mapping = {
        "suma": "Suma de decimales",
        "resta": "Resta de decimales",
        "multiplicacion": "Multiplicación de decimales",
        "division": "División de decimales",
        "+": "Suma de decimales",
        "-": "Resta de decimales",
        "×": "Multiplicación de decimales",
        "÷": "División de decimales",
    }
    return mapping.get(key.lower(), key.capitalize())
