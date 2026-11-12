"""
Parámetros del núcleo de práctica.

Ningún valor ajustable va fijo en el código (docs/DISENO_MODULAR.md, sección 1 → Dominio por
lección, y pregunta abierta 4): todos están aquí con su valor provisional, y se pueden cambiar
sin tocar el código con filas `nucleo.<campo>` en la tabla `configuracion_sistema`
(por ejemplo `nucleo.opciones_banco = 4`).

Un valor mal escrito o fuera de rango en la tabla no detiene la práctica: se registra en el log
y se usa el valor por defecto de ese campo.
"""

import logging
from dataclasses import dataclass, fields, replace
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PREFIJO = "nucleo."


@dataclass(frozen=True)
class ParametrosNucleo:
    # --- Problema y banco (fase 3a) ---
    intentos_por_problema: int = 3
    opciones_banco: int = 3                 # entre 3 y 4
    proporcion_azar_signo: float = 0.5      # probabilidad de MOSTRAR el signo en modo "al azar"
    proporcion_azar_iconos: float = 0.5     # probabilidad de mostrar los íconos en modo "al azar"
    grado_maximo_banco: int = 2             # hasta este grado, siempre banco
    grado_minimo_teclado: int = 4           # desde este grado, siempre teclado (entre ambos: según la lección)

    # --- Dominio por lección (fase 3b) ---
    ventana_dominio: int = 10               # últimos N problemas de la lección
    umbral_dominio: float = 0.8             # aciertos mínimos en la ventana
    dias_distintos_dominio: int = 2         # la ventana debe abarcar al menos N días distintos
    dias_para_repaso: int = 14              # sin practicar una lección dominada → repaso
    ventana_repaso: int = 5                 # primeros N problemas tras vencer el repaso
    umbral_repaso: float = 0.6              # por debajo, la lección vuelve a "en progreso"
    desfase_horario_horas: int = -5         # Panamá (UTC−5, sin horario de verano): para contar días

    # --- Reparto de la sesión ---
    problemas_por_sesion: int = 10
    fraccion_prioridad: float = 0.5         # parte de la sesión para las lecciones prioritarias
    max_prioritarias: int = 3               # lecciones prioritarias a la vez por salón
    nuevas_por_sesion: int = 1              # lecciones no iniciadas que se introducen por sesión
    max_lecciones_resto: int = 3            # lecciones distintas en la parte general de la sesión
    problemas_extension: int = 2            # zona de extensión: problemas por sesión
    problemas_refuerzo: int = 2             # zona de refuerzo: problemas por sesión
    umbral_refuerzo: float = 0.6            # una lección "falla" con menos de esta precisión…
    minimo_resultados_refuerzo: int = 5     # …medida sobre al menos estos problemas
    fallos_pausa_extension: int = 2         # fallos en la extensión que la pausan
    dias_pausa_extension: int = 7

    # --- Pistas y experiencia ---
    costo_pista_nivel_3: int = 0            # puntos del saldo; 0 = gratis
    xp_practica: int = 1                    # por problema terminado
    xp_acierto: int = 2                     # por problema resuelto al primer intento
    xp_bono_dominio: int = 50               # al dominar una lección (la fórmula del nivel es de la fase 7)

    def __post_init__(self):
        if self.intentos_por_problema < 1:
            raise ValueError("intentos_por_problema debe ser al menos 1")
        if not 3 <= self.opciones_banco <= 4:
            raise ValueError("opciones_banco debe estar entre 3 y 4")
        for nombre in ("proporcion_azar_signo", "proporcion_azar_iconos"):
            if not 0 <= getattr(self, nombre) <= 1:
                raise ValueError(f"{nombre} debe estar entre 0 y 1")
        if not 1 <= self.grado_maximo_banco < self.grado_minimo_teclado <= 7:
            raise ValueError("Debe cumplirse 1 <= grado_maximo_banco < grado_minimo_teclado <= 7")
        for nombre in ("umbral_dominio", "umbral_repaso", "umbral_refuerzo", "fraccion_prioridad"):
            if not 0 <= getattr(self, nombre) <= 1:
                raise ValueError(f"{nombre} debe estar entre 0 y 1")
        for nombre in ("ventana_dominio", "dias_distintos_dominio", "dias_para_repaso", "ventana_repaso",
                       "problemas_por_sesion", "max_prioritarias", "max_lecciones_resto",
                       "fallos_pausa_extension", "minimo_resultados_refuerzo"):
            if getattr(self, nombre) < 1:
                raise ValueError(f"{nombre} debe ser al menos 1")
        for nombre in ("nuevas_por_sesion", "problemas_extension", "problemas_refuerzo",
                       "dias_pausa_extension", "costo_pista_nivel_3", "xp_practica", "xp_acierto",
                       "xp_bono_dominio"):
            if getattr(self, nombre) < 0:
                raise ValueError(f"{nombre} no puede ser negativo")
        if not -12 <= self.desfase_horario_horas <= 14:
            raise ValueError("desfase_horario_horas debe estar entre -12 y 14")


_CONVERSORES = {int: int, float: float, bool: lambda v: v.strip().lower() in ("1", "true", "si", "sí")}


def parametros_desde_config(valores: Mapping[str, str]) -> ParametrosNucleo:
    """Aplica sobre los valores por defecto las claves `nucleo.*` de configuracion_sistema."""
    parametros = ParametrosNucleo()
    tipos = {f.name: f.type for f in fields(ParametrosNucleo)}
    for clave, crudo in valores.items():
        if not clave.startswith(PREFIJO):
            continue
        campo = clave[len(PREFIJO):]
        if campo not in tipos:
            logger.warning("Parámetro del núcleo desconocido: %s", clave)
            continue
        tipo = tipos[campo]
        tipo = {"int": int, "float": float, "bool": bool}.get(tipo, tipo)
        try:
            parametros = replace(parametros, **{campo: _CONVERSORES[tipo](str(crudo))})
        except (ValueError, TypeError) as e:
            logger.warning("Parámetro %s=%r inválido (%s); se usa el valor por defecto", clave, crudo, e)
    return parametros


async def cargar_parametros(db: AsyncSession) -> ParametrosNucleo:
    """Parámetros vigentes: los valores por defecto con lo que haya en configuracion_sistema."""
    from app.models.config import ConfiguracionSistema

    filas = await db.execute(
        select(ConfiguracionSistema.clave, ConfiguracionSistema.valor)
        .where(ConfiguracionSistema.clave.like(PREFIJO + "%"))
    )
    return parametros_desde_config({clave: valor for clave, valor in filas if valor is not None})
