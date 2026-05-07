"""
Service para generación de enunciados narrativos temáticos.

Genera enunciados con DeepSeek V3 y los cachea permanentemente
en tabla enunciado_tematico (PK: signature × tema × nivel).
"""

from typing import Dict, List

from app.repositories.enunciados_repository import EnunciadoTematicoRepository
from app.services.llm_service import LLMService, LLMPrompts
from app.models.problem import Problema


# Mapeo del Operacion enum (símbolos) a nombres legibles para el LLM
_OP_NOMBRE: Dict[str, str] = {
    "+": "suma",
    "-": "resta",
    "×": "multiplicacion",
    "÷": "division",
}


class EnunciadosService:
    """Service para enunciados narrativos temáticos con caché LLM."""

    def __init__(
        self,
        enunciados_repo: EnunciadoTematicoRepository,
        llm_service: LLMService,
    ):
        self.enunciados_repo = enunciados_repo
        self.llm_service = llm_service

    # ──────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────

    async def obtener_enunciado(
        self,
        problema_id: int,
        tema_nombre: str,
    ) -> str:
        """
        Obtiene enunciado narrativo para un problema + tema.

        Flujo:
        1. Normaliza el nombre del tema ("Piratas" → "tema-piratas")
        2. Busca en caché  (signature × tema × nivel)
        3. Si miss → genera con DeepSeek V3 → guarda → devuelve
        4. Si hit  → devuelve directo sin llamar al LLM

        Returns:
            Texto del enunciado narrativo (puede ser fallback genérico).
        """
        problema = await self.enunciados_repo.get_problema(problema_id)
        if not problema:
            raise ValueError(f"Problema {problema_id} no encontrado")

        tema = self._normalizar_tema(tema_nombre)

        # Guardia: solo temas narrativos conocidos generan enunciados.
        # Temas como "Clásico" / "tema-default" NO son narrativos y no deben
        # generar texto LLM (evita el fallback-a-piratas de _buscar_config_tema).
        if tema not in LLMPrompts._TEMAS_CONFIG:
            raise ValueError(f"Tema '{tema}' no es narrativo — sin enunciado")

        signature = problema.signature
        nivel = problema.nivel_dificultad

        # 1. Buscar en caché
        cached = await self.enunciados_repo.get(signature, tema, nivel)
        if cached:
            return cached.texto

        # 2. Generar con LLM
        texto = await self._generar_con_llm(problema, tema)

        # 3. Guardar en caché (permanente)
        await self.enunciados_repo.create(signature, tema, nivel, texto)

        return texto

    async def obtener_enunciados_lote(
        self,
        problema_ids: List[int],
        tema_nombre: str,
    ) -> Dict[int, str]:
        """
        Obtiene enunciados para múltiples problemas de una sesión.

        Diseñado para llamarse al inicio de la sesión con todos los
        problema_ids. Los hits de caché son instantáneos; el LLM solo
        se llama para los que no tienen texto aún.

        Returns:
            Dict {problema_id: texto} — solo incluye los que se obtuvieron
            correctamente; los fallidos se omiten (el frontend usa la
            pregunta genérica como fallback).
        """
        resultado: Dict[int, str] = {}
        for problema_id in problema_ids:
            try:
                texto = await self.obtener_enunciado(problema_id, tema_nombre)
                resultado[problema_id] = texto
            except Exception:
                # Silencioso: no bloquea la sesión si un enunciado falla
                pass
        return resultado

    # ──────────────────────────────────────────────────────────────
    # Helpers privados
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalizar_tema(tema: str) -> str:
        """
        Normaliza el nombre del tema a formato "tema-X".

        Ejemplos:
            "Piratas"       → "tema-piratas"
            "tema-piratas"  → "tema-piratas"
            "ASTRONAUTAS"   → "tema-astronautas"
        """
        tema = tema.lower().strip()
        if not tema.startswith("tema-"):
            tema = f"tema-{tema}"
        return tema

    async def _generar_con_llm(self, problema: Problema, tema: str) -> str:
        """
        Genera enunciado narrativo con DeepSeek V3.

        IMPORTANTE: Las excepciones se propagan al llamador.
        Si el LLM falla, NO se guarda ningún fallback en caché;
        el llamador decidirá qué mostrar.
        """
        op_nombre = _OP_NOMBRE.get(problema.operacion.value, problema.operacion.value)
        num1 = float(problema.numero1)
        num2 = float(problema.numero2)

        prompt = LLMPrompts.generar_enunciado_narrativo(
            operacion=op_nombre,
            operando1=num1,
            operando2=num2,
            tema=tema,
            variacion=1,
        )

        # Sin try/except aquí: si falla, la excepción sube y NO se cachea nada
        respuesta = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.8,
            max_tokens=200,
        )
        texto = respuesta.strip()
        if not texto:
            raise ValueError("DeepSeek devolvió respuesta vacía")
        return texto

    @staticmethod
    def _fallback_por_id(problema_id: int) -> str:
        """
        Fallback cuando el problema no se encuentra en BD.
        No se cachea — se lanza excepción en obtener_enunciado.
        """
        raise ValueError(f"Problema {problema_id} no encontrado")
