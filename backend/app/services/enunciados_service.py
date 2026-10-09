"""
Service para generación de enunciados narrativos temáticos.

Genera hasta 3 variaciones por problema con DeepSeek V3 (una sola llamada) y las
cachea permanentemente en la tabla enunciado_tematico
(PK: signature × tema × nivel × variacion). Al servir un problema se elige una
variación al azar. Solo se guardan variaciones que contienen exactamente los
números del problema.
"""

import asyncio
import random
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Set

from sqlalchemy.exc import IntegrityError

from app.models.problem import Problema
from app.repositories.enunciados_repository import EnunciadoTematicoRepository
from app.services.llm_service import LLMPrompts, LLMService

# Mapeo del Operacion enum (símbolos) a nombres legibles para el LLM
_OP_NOMBRE: Dict[str, str] = {
    "+": "suma",
    "-": "resta",
    "×": "multiplicacion",
    "÷": "division",
}

NUM_VARIACIONES = 3
MAX_INTENTOS_GENERACION = 2   # llamadas al LLM si ninguna variación sale válida
MAX_PROBLEMAS_POR_LOTE = 30

_RE_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
_RE_VARIACION = re.compile(r"^\s*VARIACION_\d+\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


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

    async def obtener_enunciado(self, problema_id: int, tema_nombre: str) -> str:
        """
        Enunciado narrativo de un problema + tema (variación al azar entre las guardadas).

        Lanza ValueError si el tema no es narrativo, el problema no existe o el LLM
        no produjo ningún texto válido.
        """
        if LLMPrompts.resolver_tema(tema_nombre) is None:
            raise ValueError(f"Tema '{tema_nombre}' no es narrativo — sin enunciado")
        resultado = await self.obtener_enunciados_lote([problema_id], tema_nombre)
        if problema_id not in resultado:
            raise ValueError(f"No se pudo obtener enunciado para el problema {problema_id}")
        return resultado[problema_id]

    async def obtener_enunciados_lote(
        self,
        problema_ids: List[int],
        tema_nombre: str,
        permitidos: Optional[Set[int]] = None,
    ) -> Dict[int, str]:
        """
        Enunciados para varios problemas de una sesión.

        1. Lee la caché (secuencial: la sesión de BD no admite uso concurrente).
        2. Genera en paralelo (asyncio.gather) los que faltan, sin tocar la BD.
        3. Guarda las variaciones válidas (secuencial).

        Args:
            permitidos: si se indica, solo se atienden los problemas de este conjunto.

        Returns:
            {problema_id: texto} solo para los obtenidos; los fallidos se omiten
            (el frontend usa la pregunta genérica).
        """
        tema = LLMPrompts.resolver_tema(tema_nombre)
        if tema is None:
            return {}

        ids = list(dict.fromkeys(problema_ids))[:MAX_PROBLEMAS_POR_LOTE]
        if permitidos is not None:
            ids = [i for i in ids if i in permitidos]

        resultado: Dict[int, str] = {}
        faltantes: Dict[str, Problema] = {}          # signature → problema
        ids_por_signature: Dict[str, List[int]] = {}

        # 1. Caché
        for pid in ids:
            try:
                problema = await self.enunciados_repo.get_problema(pid)
                if problema is None:
                    continue
                cached = await self.enunciados_repo.get_variaciones(
                    problema.signature, tema, problema.nivel_dificultad
                )
            except Exception:
                continue
            if cached:
                resultado[pid] = random.choice(cached).texto
            else:
                faltantes.setdefault(problema.signature, problema)
                ids_por_signature.setdefault(problema.signature, []).append(pid)

        if not faltantes:
            return resultado

        # 2. Generación en paralelo (return_exceptions: un fallo no cancela a los demás)
        firmas = list(faltantes)
        generados = await asyncio.gather(
            *(self._generar_variaciones(faltantes[f], tema) for f in firmas),
            return_exceptions=True,
        )

        # 3. Guardado
        for firma, textos in zip(firmas, generados):
            if isinstance(textos, BaseException) or not textos:
                continue
            problema = faltantes[firma]
            guardados = await self._guardar(problema, tema, textos)
            if not guardados:
                continue
            for pid in ids_por_signature[firma]:
                resultado[pid] = random.choice(guardados)
        return resultado

    # ──────────────────────────────────────────────────────────────
    # Helpers privados
    # ──────────────────────────────────────────────────────────────

    async def _guardar(self, problema: Problema, tema: str, textos: List[str]) -> List[str]:
        """Guarda las variaciones; si otra petición ya las guardó, devuelve las existentes."""
        try:
            await self.enunciados_repo.guardar_variaciones(
                problema.signature, tema, problema.nivel_dificultad, textos
            )
            return textos
        except IntegrityError:
            await self.enunciados_repo.db.rollback()
            existentes = await self.enunciados_repo.get_variaciones(
                problema.signature, tema, problema.nivel_dificultad
            )
            return [e.texto for e in existentes]
        except Exception:
            await self.enunciados_repo.db.rollback()
            return []

    async def _generar_variaciones(self, problema: Problema, tema: str) -> List[str]:
        """
        Pide al LLM hasta NUM_VARIACIONES enunciados y devuelve solo los que contienen
        exactamente los números del problema. Si ninguno es válido reintenta una vez.
        Las excepciones del LLM se propagan; nunca se cachea nada inválido.
        """
        op_nombre = _OP_NOMBRE.get(problema.operacion.value, problema.operacion.value)
        prompt = LLMPrompts.enunciados_variaciones(
            operacion=op_nombre,
            operando1=problema.numero1,
            operando2=problema.numero2,
            tema=tema,
            cantidad=NUM_VARIACIONES,
        )
        for _ in range(MAX_INTENTOS_GENERACION):
            respuesta = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.8,
                max_tokens=500,
            )
            validos = [
                t
                for t in self.parsear_variaciones(respuesta)
                if self.contiene_numeros_exactos(t, problema.numero1, problema.numero2)
            ]
            if validos:
                return validos[:NUM_VARIACIONES]
        raise ValueError("El modelo no produjo ningún enunciado con los números correctos")

    @staticmethod
    def parsear_variaciones(respuesta: str) -> List[str]:
        """Extrae los textos de las líneas `VARIACION_n: texto` (sin comillas)."""
        textos = [m.group(1).strip().strip('"“”').strip() for m in _RE_VARIACION.finditer(respuesta)]
        return [t for t in textos if t]

    @staticmethod
    def contiene_numeros_exactos(texto: str, numero1, numero2) -> bool:
        """
        True si los números escritos en el texto son exactamente los del problema:
        ni falta ninguno ni aparece otro distinto (las cifras con coma decimal cuentan).
        """
        try:
            esperados = {Decimal(str(numero1)).normalize(), Decimal(str(numero2)).normalize()}
            encontrados = {
                Decimal(m.replace(",", ".")).normalize() for m in _RE_NUMERO.findall(texto)
            }
        except InvalidOperation:
            return False
        return encontrados == esperados
