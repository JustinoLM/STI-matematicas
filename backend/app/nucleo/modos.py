"""
Modos de presentación y de respuesta de un problema.

- Signo e íconos (por lección, los elige el profesor): siempre, nunca o al azar. Ocultar el signo
  convierte el operador en un hueco de opción (ejercicio de identificar la operación).
- Banco o teclado: según el grado del estudiante (siempre banco hasta `grado_maximo_banco`,
  según la lección en los grados intermedios, teclado desde `grado_minimo_teclado`). El profesor
  puede forzar el banco a un estudiante como adaptación de accesibilidad.

Se usa el grado del estudiante (el de su salón), no el de la lección: la destreza con el
teclado es del niño, aunque practique una lección de otro grado.

Todo es puro: recibe un `random.Random` para que las pruebas sean reproducibles.
"""

import random
from dataclasses import dataclass
from enum import Enum

from app.nucleo.parametros import ParametrosNucleo


class Modo(str, Enum):
    SIEMPRE = "siempre"
    NUNCA = "nunca"
    AZAR = "azar"


class ModoRespuesta(str, Enum):
    BANCO = "banco"
    TECLADO = "teclado"


@dataclass(frozen=True)
class ConfigModosLeccion:
    """Configuración del profesor para una lección (en 3b sale de la habilitación del salón)."""
    signo: Modo = Modo.SIEMPRE
    iconos: Modo = Modo.SIEMPRE


@dataclass(frozen=True)
class ModosProblema:
    """Modos ya resueltos para un problema concreto."""
    mostrar_signo: bool = True
    mostrar_iconos: bool = False
    respuesta: ModoRespuesta = ModoRespuesta.BANCO
    opciones_banco: int = 3

    def a_dict(self) -> dict:
        return {
            "mostrar_signo": self.mostrar_signo,
            "mostrar_iconos": self.mostrar_iconos,
            "respuesta": self.respuesta.value,
            "opciones_banco": self.opciones_banco,
        }

    @classmethod
    def desde_dict(cls, d: dict) -> "ModosProblema":
        return cls(
            mostrar_signo=bool(d["mostrar_signo"]),
            mostrar_iconos=bool(d["mostrar_iconos"]),
            respuesta=ModoRespuesta(d["respuesta"]),
            opciones_banco=int(d["opciones_banco"]),
        )


def resolver_binario(modo: Modo, proporcion: float, rng: random.Random) -> bool:
    """True si se muestra: siempre → sí, nunca → no, al azar → con probabilidad `proporcion`."""
    if modo == Modo.SIEMPRE:
        return True
    if modo == Modo.NUNCA:
        return False
    return rng.random() < proporcion


def resolver_modo_respuesta(
    grado_estudiante: int,
    banco_en_grados_intermedios: bool,
    banco_forzado: bool,
    parametros: ParametrosNucleo,
) -> ModoRespuesta:
    """Banco o teclado. El banco forzado por el profesor manda sobre todo lo demás."""
    if banco_forzado or grado_estudiante <= parametros.grado_maximo_banco:
        return ModoRespuesta.BANCO
    if grado_estudiante >= parametros.grado_minimo_teclado:
        return ModoRespuesta.TECLADO
    return ModoRespuesta.BANCO if banco_en_grados_intermedios else ModoRespuesta.TECLADO


def resolver_modos(
    config: ConfigModosLeccion,
    *,
    grado_estudiante: int,
    banco_forzado: bool,
    admite_signo_oculto: bool,
    admite_iconos: bool,
    banco_en_grados_intermedios: bool,
    parametros: ParametrosNucleo,
    rng: random.Random,
) -> ModosProblema:
    """Modos de un problema a partir de la configuración de la lección y del estudiante.

    Si la lección no admite ocultar el signo (no tiene operador) o no tiene íconos, la
    configuración del profesor no aplica: el signo se muestra y los íconos no."""
    mostrar_signo = (
        resolver_binario(config.signo, parametros.proporcion_azar_signo, rng)
        if admite_signo_oculto else True
    )
    mostrar_iconos = (
        resolver_binario(config.iconos, parametros.proporcion_azar_iconos, rng)
        if admite_iconos else False
    )
    return ModosProblema(
        mostrar_signo=mostrar_signo,
        mostrar_iconos=mostrar_iconos,
        respuesta=resolver_modo_respuesta(
            grado_estudiante, banco_en_grados_intermedios, banco_forzado, parametros
        ),
        opciones_banco=parametros.opciones_banco,
    )
