"""
Service para mensajes motivacionales personalizados con DeepSeek V3.

Genera mensajes para el dashboard y la página de progreso del estudiante.
Caché diaria: un mensaje por (estudiante_id, tipo, fecha, tema).
Si el estudiante cambia de tema, se genera un nuevo mensaje ese día.
"""

from datetime import date
from typing import Optional

from app.repositories.mensajes_repository import MensajesRepository
from app.services.llm_service import LLMService, LLMPrompts
from app.models.user import Estudiante


class MensajesService:
    """Servicio de mensajes motivacionales con caché diaria."""

    def __init__(
        self,
        mensajes_repo: MensajesRepository,
        llm_service: LLMService,
    ):
        self.mensajes_repo = mensajes_repo
        self.llm_service = llm_service

    async def obtener_mensaje(
        self,
        estudiante: Estudiante,
        tipo: str,
        nivel_general: int = 1,
        tema: Optional[str] = None,
    ) -> tuple[str, bool]:
        """
        Obtiene mensaje motivacional para el estudiante.

        Flujo:
        1. Busca en caché (estudiante_id, tipo, hoy, tema)
        2. Si hit  → devuelve cached, generada_llm=False
        3. Si miss → genera con V3 → guarda → devuelve, generada_llm=True

        Args:
            tema: Nombre normalizado del tema activo (ej. "tema-piratas")
                  None si el estudiante no tiene tema activo.

        Returns:
            (texto, generada_llm)
        """
        hoy = date.today()
        nombre = estudiante.nombre_completo
        genero_val = getattr(estudiante, "genero", None)
        genero = genero_val.value if hasattr(genero_val, "value") else str(genero_val or "masculino")

        # 1. Buscar en caché (clave incluye tema)
        cached = await self.mensajes_repo.get(estudiante.id, tipo, hoy, tema)
        if cached:
            return cached.texto, False

        # 2. Generar con LLM
        try:
            texto = await self._generar(nombre, genero, tipo, nivel_general, tema)
        except Exception:
            # Si el LLM falla, devolver mensaje genérico sin cachear
            texto = self._fallback(nombre, tipo, tema)
            return texto, False

        # 3. Guardar en caché (incluye tema para la próxima consulta)
        await self.mensajes_repo.create(estudiante.id, tipo, texto, hoy, tema)
        return texto, True

    async def _generar(
        self,
        nombre: str,
        genero: str,
        tipo: str,
        nivel_general: int,
        tema: Optional[str],
    ) -> str:
        if tipo == "dashboard":
            prompt = LLMPrompts.mensaje_motivacional_dashboard(
                nombre, genero, nivel_general, tema
            )
        else:
            prompt = LLMPrompts.mensaje_motivacional_progreso(nombre, genero, tema)

        respuesta = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.8,
            max_tokens=120,
        )
        texto = respuesta.strip()
        if not texto:
            raise ValueError("LLM devolvió respuesta vacía")
        return texto

    @staticmethod
    def _fallback(nombre: str, tipo: str, tema: Optional[str]) -> str:
        primer_nombre = nombre.split()[0] if nombre else "estudiante"
        # Usar saludo temático si está disponible
        saludo_tema = ""
        if tema:
            config = LLMPrompts._buscar_config_tema(tema)
            saludo_tema = config.get("saludo", "")

        if tipo == "dashboard":
            base = f"¡Bienvenido, {primer_nombre}! ¡Hoy es un gran día para practicar matemáticas!"
        else:
            base = f"¡Sigue adelante, {primer_nombre}! Cada práctica te hace más fuerte."

        return f"{saludo_tema} {base}".strip() if saludo_tema else base
