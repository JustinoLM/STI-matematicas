"""
Service para comunicación con DeepSeek API.

Reemplaza ollama_service.py — usa DeepSeek API directamente (compatible con OpenAI).
- V3 (deepseek-chat): mensajes, enunciados, motivación
- R1 (deepseek-reasoner): análisis post-práctica
"""

import httpx
import time
from typing import Optional, Dict
from fastapi import HTTPException, status

from app.core.config import settings


class LLMService:
    """Service para interactuar con DeepSeek API."""

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.model_v3 = settings.DEEPSEEK_MODEL_V3      # deepseek-chat
        self.model_r1 = settings.DEEPSEEK_MODEL_R1      # deepseek-reasoner
        self.model = self.model_v3                       # alias por compatibilidad
        self.timeout = 60
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_reasoning: bool = False,
    ) -> str:
        """
        Genera texto usando DeepSeek API.

        Args:
            prompt: Mensaje del usuario
            system: System prompt opcional
            temperature: Temperatura (0-1). Ignorado en R1.
            max_tokens: Máximo de tokens a generar
            use_reasoning: Si True usa R1 (razonamiento), si False usa V3

        Returns:
            Texto generado
        """
        model = self.model_r1 if use_reasoning else self.model_v3

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        # R1 no acepta temperature
        if not use_reasoning:
            payload["temperature"] = temperature

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Timeout al comunicarse con DeepSeek después de {self.timeout}s",
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error en DeepSeek API ({e.response.status_code}): {e.response.text}",
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error al comunicarse con DeepSeek: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado con LLM: {str(e)}",
            )

    async def check_health(self) -> Dict:
        """Verifica que la API de DeepSeek esté disponible."""
        try:
            # Llamada mínima para verificar conectividad
            await self.generate(
                prompt="Responde solo 'ok'",
                max_tokens=5,
            )
            return {
                "status": "healthy",
                "provider": "deepseek",
                "model_v3": self.model_v3,
                "model_r1": self.model_r1,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "deepseek",
                "error": str(e),
            }

    async def close(self):
        """Cierra el cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ============================================
# Prompts Pre-definidos
# ============================================

class LLMPrompts:
    """Biblioteca de prompts para diferentes tareas."""

    # ── Pistas (nivel 3) ────────────────────────────────────────────────────

    @staticmethod
    def generar_pista_nivel_3(
        operacion: str,
        operando1: float,
        operando2: float,
        resultado: float,
        respuesta_incorrecta: float,
    ) -> str:
        """Prompt para generar pista nivel 3 — V3."""
        return f"""Eres un tutor de matemáticas para niños de 5to grado (10-11 años).

Un estudiante está resolviendo: {operando1} {operacion} {operando2}

La respuesta correcta es: {resultado}
La respuesta del estudiante fue: {respuesta_incorrecta}

Tu tarea: Genera una pista que casi revele la respuesta pero sin darla directamente.

Reglas:
- Máximo 2-3 oraciones
- Usa lenguaje simple para niños de 10-11 años
- No uses la palabra "respuesta correcta" ni reveles el número exacto
- Guía hacia el proceso correcto
- Sé alentador y positivo

Ejemplo de pista buena:
"Si multiplicas los números sin los puntos decimales obtienes 4000. Ahora piensa: ¿cuántos decimales hay en total? Coloca el punto contando desde la derecha."

Genera la pista:"""

    # ── Enunciados narrativos ────────────────────────────────────────────────

    # Configuración rica de los 6 temas narrativos.
    # Las claves usan el formato normalizado de _normalizar_tema():
    #   "tema-" + nombre.lower().strip()
    # Ej: "tema-piratas" (id del shop.ts)
    _TEMAS_CONFIG: dict = {
        "tema-piratas": {
            "nombre": "Piratas de los Mares",
            "contexto": "repartir tesoros y botines entre la tripulación, calcular distancias entre islas en alta mar, negociar en puertos y tabernas costeras",
            "saludo": "¡Arrr! ¡Excelente cálculo, marinero!",
            "personajes": ["el Capitán pirata", "la corsaria", "el grumete", "la tripulación del galeón"],
            "objetos": ["monedas de oro", "cofres del tesoro", "perlas del mar", "joyas capturadas", "barriles de ron", "mapas del tesoro"],
            "verbos": ["encontró", "capturó", "descubrió", "repartió", "saqueó", "escondió"],
            "lugares": ["la isla del tesoro", "el barco pirata", "la cueva secreta", "el puerto", "alta mar"],
        },
        "tema-astronautas galácticos": {
            "nombre": "Astronautas Galácticos",
            "contexto": "mezclar combustibles para el cohete, calcular órbitas y distancias entre planetas, gestionar provisiones en la estación espacial",
            "saludo": "¡Misión cumplida, comandante!",
            "personajes": ["el astronauta", "la comandante", "el científico espacial", "la tripulación orbital"],
            "objetos": ["unidades de combustible", "muestras lunares", "módulos de oxígeno", "cristales espaciales", "contenedores de agua"],
            "verbos": ["recogió", "consumió", "almacenó", "transportó", "analizó", "cargó"],
            "lugares": ["la estación espacial", "la nave Apolo", "el planeta Marte", "el módulo lunar", "el laboratorio orbital"],
        },
        "tema-magos de la academia": {
            "nombre": "Magos de la Academia",
            "contexto": "preparar pociones mágicas con ingredientes exactos, calcular el poder de los hechizos, distribuir ingredientes entre aprendices",
            "saludo": "¡Conjuro perfecto, joven mago!",
            "personajes": ["el aprendiz de mago", "la hechicera Merlina", "el maestro Aldo", "los estudiantes de magia"],
            "objetos": ["frascos de poción", "gramos de polvo de estrellas", "cristales encantados", "ingredientes mágicos", "hechizos"],
            "verbos": ["conjuró", "preparó", "mezcló", "distribuyó", "descubrió", "encantó"],
            "lugares": ["la torre de la academia", "el laboratorio de pociones", "la biblioteca mágica", "el bosque encantado"],
        },
        "tema-caballeros del reino": {
            "nombre": "Caballeros del Reino",
            "contexto": "repartir provisiones para la batalla, medir distancias entre castillos, distribuir armaduras y equipos de guerra entre los caballeros",
            "saludo": "¡Honor al campeón matemático!",
            "personajes": ["el caballero Sir Rodrigo", "la dama guerrera", "el rey", "el escudero", "los soldados del reino"],
            "objetos": ["bolsas de provisiones", "armaduras de hierro", "escudos", "espadas", "monedas del reino", "flechas"],
            "verbos": ["repartió", "conquistó", "distribuyó", "protegió", "ganó", "entregó"],
            "lugares": ["el castillo real", "el campo de batalla", "el torneo", "la aldea", "las murallas del reino"],
        },
        "tema-vaqueros del oeste": {
            "nombre": "Vaqueros del Oeste",
            "contexto": "comercio de ganado en la feria del pueblo, medir terrenos del rancho, repartir ganancias entre vaqueros después del rodeo",
            "saludo": "¡Yeehaw! ¡Cálculo certero, vaquero!",
            "personajes": ["el vaquero Billy", "la ranchera", "el sheriff", "el comerciante", "los cowboys del rancho"],
            "objetos": ["cabezas de ganado", "acres de terreno", "dólares de oro", "sacos de harina", "caballos", "balas de heno"],
            "verbos": ["vendió", "compró", "midió", "repartió", "ganó", "intercambió"],
            "lugares": ["el rancho", "el pueblo del oeste", "la feria de ganado", "la pradera", "el salón"],
        },
        "tema-princesas inventoras": {
            "nombre": "Princesas y Príncipes Inventores",
            "contexto": "construir inventos con materiales exactos, medir piezas para máquinas y robots, calcular materiales para edificar construcciones del reino",
            "saludo": "¡Brillante ingenio, alteza!",
            "personajes": ["la Princesa Inventora", "el Príncipe Ingeniero", "el asistente del laboratorio", "la científica real"],
            "objetos": ["engranajes", "piezas de metal", "tornillos", "metros de cable eléctrico", "cristales del laboratorio", "resortes"],
            "verbos": ["construyó", "diseñó", "calculó", "fabricó", "inventó", "ensambló"],
            "lugares": ["el taller del palacio", "el laboratorio real", "la sala de máquinas", "la biblioteca de inventos"],
        },
    }

    @classmethod
    def _buscar_config_tema(cls, tema: str) -> dict:
        """
        Busca la configuración de un tema por clave exacta o parcial.
        Fallback: piratas.
        """
        # Coincidencia exacta primero
        if tema in cls._TEMAS_CONFIG:
            return cls._TEMAS_CONFIG[tema]
        # Coincidencia parcial (por si la normalización difiere levemente)
        for key, config in cls._TEMAS_CONFIG.items():
            if key in tema or tema in key:
                return config
        # Sin fallback — el llamador debe validar que el tema existe
        raise ValueError(f"Tema '{tema}' no encontrado en _TEMAS_CONFIG")

    @staticmethod
    def generar_enunciado_narrativo(
        operacion: str,
        operando1: float,
        operando2: float,
        tema: str,
        variacion: int,
    ) -> str:
        """Prompt para generar enunciado narrativo temático — V3."""

        operacion_map = {
            "suma": "juntar/sumar",
            "resta": "quitar/restar",
            "multiplicacion": "multiplicar/agrupar",
            "division": "repartir/dividir",
        }

        config = LLMPrompts._buscar_config_tema(tema)
        operacion_texto = operacion_map.get(operacion, operacion)

        return f"""Eres un escritor creativo de problemas matemáticos para niños de 5to grado (10-11 años).

Tema narrativo: {config['nombre']}
Contexto del tema: {config['contexto']}

Crea un enunciado narrativo para este problema matemático:
- Acción matemática: {operacion_texto}
- Números exactos a usar: {operando1} y {operando2}
- Variación #{variacion} — debe ser diferente a versiones anteriores

Recursos narrativos disponibles:
- Personajes: {', '.join(config['personajes'])}
- Objetos: {', '.join(config['objetos'])}
- Verbos: {', '.join(config['verbos'])}
- Lugares: {', '.join(config['lugares'])}

Reglas CRÍTICAS (cumplir todas):
1. Exactamente 1-2 oraciones
2. Termina con una pregunta matemática clara
3. Usa los números EXACTOS: {operando1} y {operando2} (¡no cambiarlos!)
4. NO menciones la operación directamente — solo plantea el contexto
5. Apropiado para niños de 10-11 años, lenguaje sencillo y emocionante

Ejemplo del estilo buscado (tema piratas, suma):
"El Capitán Barbanegra encontró un cofre con {operando1} monedas de oro en la isla del tesoro. Su tripulación capturó otro barco con {operando2} monedas más. ¿Cuántas monedas tienen en total?"

Genera SOLO el enunciado narrativo (sin comillas ni explicaciones):"""

    @classmethod
    def generar_multiples_variaciones(
        cls,
        operacion: str,
        operando1: float,
        operando2: float,
        tema: str,
        num_variaciones: int = 3,
    ) -> str:
        """Prompt para generar múltiples variaciones a la vez — V3."""
        config = cls._buscar_config_tema(tema)
        vocab_str = ", ".join(config["objetos"][:4])

        return f"""Genera {num_variaciones} enunciados narrativos DIFERENTES para este problema matemático:

Tema: {config['nombre']} — {config['contexto']}
Operación: {operacion} con los números {operando1} y {operando2}
Vocabulario clave: {vocab_str}

Reglas:
- Cada enunciado debe ser ÚNICO (diferente personaje, situación o lugar)
- Máximo 2 oraciones cada uno, termina con pregunta
- Usa los números exactos {operando1} y {operando2}
- NO menciones la operación directamente
- Lenguaje sencillo para niños de 10-11 años

Formato ESTRICTO:
VARIACION_1: [enunciado]
VARIACION_2: [enunciado]
VARIACION_3: [enunciado]

Genera ahora:"""

    # ── Mensajes motivacionales ──────────────────────────────────────────────

    @classmethod
    def mensaje_motivacional_dashboard(
        cls,
        nombre: str,
        genero: str,
        nivel_general: int,
        tema: Optional[str] = None,
    ) -> str:
        """Prompt para mensaje motivacional del dashboard — V3."""
        articulo = "el" if genero == "masculino" else "la"

        # Contexto temático opcional
        tema_section = ""
        if tema:
            config = cls._buscar_config_tema(tema)
            tema_section = (
                f"\nUso temático OBLIGATORIO:\n"
                f"- Universo narrativo del estudiante: {config['nombre']}\n"
                f"- Saludo característico del tema: \"{config['saludo']}\"\n"
                f"- Incluye UNA referencia sutil al universo (un personaje, objeto o lugar del tema)\n"
            )

        return f"""Eres un tutor motivador para niños de 5to grado (10-11 años).

Estudiante: {nombre}
Género: {genero}
Nivel general: {nivel_general} de 5
{tema_section}
Escribe un mensaje de bienvenida corto y entusiasta para {articulo} estudiante {nombre}.

Reglas:
- Máximo 2 oraciones
- Usa el nombre del estudiante
- Menciona el nivel de forma positiva
- Usa lenguaje apropiado para niños de 10-11 años
- Sé animado y alentador
- Conjuga adjetivos según el género ({genero})
- Si hay tema, úsalo de forma natural (no lo forces)

Ejemplos sin tema:
"¡Bienvenida, Sofía! Estás en nivel 3, ¡eres una crack de las matemáticas!"

Ejemplo con tema piratas:
"¡Arrr! ¡Bienvenido de vuelta, Carlos! En nivel 2 ya eres digno marinero de las matemáticas."

Genera SOLO el mensaje (sin comillas ni explicaciones):"""

    @classmethod
    def mensaje_motivacional_progreso(
        cls,
        nombre: str,
        genero: str,
        tema: Optional[str] = None,
    ) -> str:
        """Prompt para mensaje motivacional de la página de progreso — V3."""

        # Contexto temático opcional
        tema_section = ""
        if tema:
            config = cls._buscar_config_tema(tema)
            tema_section = (
                f"\nUso temático OBLIGATORIO:\n"
                f"- Universo narrativo: {config['nombre']}\n"
                f"- Saludo del tema: \"{config['saludo']}\"\n"
                f"- Incluye UNA referencia al universo (objeto o acción del tema)\n"
            )

        return f"""Eres un tutor motivador para niños de 5to grado (10-11 años).

Estudiante: {nombre}
Género: {genero}
{tema_section}
Escribe un mensaje corto de motivación para animar a {nombre} a revisar su progreso y seguir mejorando.

Reglas:
- Máximo 2 oraciones
- Menciona el nombre
- Motiva a seguir practicando y a revisar sus estadísticas
- Apropiado para niños de 10-11 años
- Conjuga adjetivos según el género ({genero})
- Si hay tema, úsalo de forma natural

Ejemplo con tema astronautas:
"¡Misión cumplida, Ana! Revisa tus estadísticas y sigue entrenando para conquistar la galaxia de las matemáticas."

Genera SOLO el mensaje (sin comillas ni explicaciones):"""

    # ── Análisis post-práctica ───────────────────────────────────────────────

    @staticmethod
    def analisis_post_practica(
        nombre: str,
        genero: str,
        operacion: str,
        nivel: int,
        total_problemas: int,
        total_correctos: int,
        precision: float,
        tiempo_promedio_seg: float,
        pasos_intermedios_correctos: int,
        pasos_intermedios_total: int,
    ) -> str:
        """Prompt para análisis post-práctica — R1."""
        precision_pct = round(precision * 100, 1)
        pasos_pct = (
            round((pasos_intermedios_correctos / pasos_intermedios_total) * 100, 1)
            if pasos_intermedios_total > 0
            else None
        )
        pasos_info = (
            f"Pasos intermedios correctos: {pasos_intermedios_correctos}/{pasos_intermedios_total} ({pasos_pct}%)"
            if pasos_pct is not None
            else "Sin datos de pasos intermedios"
        )

        return f"""Eres un tutor de matemáticas para niños de 5to grado. Analiza la sesión de práctica de un estudiante.

Estudiante: {nombre} (género: {genero})
Operación practicada: {operacion}
Nivel: {nivel} de 5
Problemas resueltos: {total_problemas}
Respuestas correctas: {total_correctos} ({precision_pct}%)
Tiempo promedio por problema: {tiempo_promedio_seg:.1f} segundos
{pasos_info}

Escribe un análisis breve y constructivo para el estudiante.

Reglas:
- Máximo 4 oraciones
- Usa el nombre del estudiante
- Destaca lo que hizo bien
- Señala una cosa concreta a mejorar (si aplica)
- Sé positivo y constructivo, nunca punitivo
- Lenguaje simple para niños de 10-11 años
- Conjuga según el género ({genero})

Genera SOLO el análisis (sin comillas ni encabezados):"""
