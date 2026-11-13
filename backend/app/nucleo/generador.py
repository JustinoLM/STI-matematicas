"""
Interfaz del generador de lección.

Cada lección del catálogo que se practica en el núcleo tiene un generador: una subclase de
GeneradorLeccion registrada en app/nucleo/registro.py. Lo propio de la lección es:

- generar(rng, modos): un problema dentro del rango de la lección, ya con los modos resueltos
  (signo oculto → el operador es un hueco de opción; íconos → cantidades por operando);
- reglas_error(): las reglas de error de sus caminos, en orden de prioridad;
- en_rango(problema): comprobación del rango de la lección (la usan las pruebas);
- es_valido(valor): qué valores pueden aparecer como opción del banco (por defecto, no negativos);
- pista(problema, nivel): el texto de los 3 niveles de pista.

Lo genérico lo da la clase base:

- crear(rng, modos): genera el problema y, en modo banco, arma el banco de cada hueco numérico;
- corregir(problema, respuestas): valida cada hueco y clasifica el error de los incorrectos.

El generador no guarda estado: todo lo que necesita después (reglas de error, pistas) sale del
problema, que se guarda como JSON. Si cambia la forma de generar, se sube `version`.
"""

import random
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, ClassVar, Sequence

from app.nucleo.banco import armar_banco
from app.nucleo.errores import ReglaError, clasificar, distractores
from app.nucleo.modos import ModoRespuesta, ModosProblema
from app.nucleo.problema import HuecoNumero, OpcionBanco, Problema, ProblemaExpresion
from app.nucleo.validacion import ResultadoValidacion, validar

NIVELES_PISTA = (1, 2, 3)


class GeneradorLeccion(ABC):
    leccion_id: ClassVar[str]
    caminos: ClassVar[tuple[str, ...]]
    version: ClassVar[int] = 1

    # Qué modos admite la lección
    admite_signo_oculto: ClassVar[bool] = False
    admite_iconos: ClassVar[bool] = False
    banco_en_grados_intermedios: ClassVar[bool] = True   # en 3.º: banco o teclado según la lección

    # Paso de los números cercanos con que se completa el banco
    paso_cercano: ClassVar[Decimal] = Decimal(1)

    # --- Lo propio de cada lección ---

    @abstractmethod
    def generar(self, rng: random.Random, modos: ModosProblema) -> Problema:
        """Problema dentro del rango de la lección, sin banco (lo arma crear())."""

    @abstractmethod
    def reglas_error(self) -> Sequence[ReglaError]:
        """Reglas de error de la lección, en orden de prioridad."""

    @abstractmethod
    def en_rango(self, problema: Problema) -> bool:
        """¿Los números del problema están dentro del rango de la lección?"""

    @abstractmethod
    def pista(self, problema: Problema, nivel: int) -> str:
        """Nivel 1: estrategia; 2: paso a paso; 3: casi la respuesta."""

    def es_valido(self, valor: Decimal) -> bool:
        """¿Puede aparecer `valor` como opción del banco? Por defecto, si no es negativo."""
        return valor >= 0

    # --- Lo genérico ---

    def crear(self, rng: random.Random, modos: ModosProblema) -> Problema:
        problema = self.generar(rng, modos)
        if problema.leccion_id != self.leccion_id or problema.generador_version != self.version:
            raise ValueError("El problema no corresponde a este generador")
        if problema.modos != modos:
            raise ValueError("El generador cambió los modos del problema")
        if modos.respuesta == ModoRespuesta.BANCO and isinstance(problema, ProblemaExpresion):
            for hueco in problema.huecos.values():
                if isinstance(hueco, HuecoNumero):
                    hueco.banco = self.banco(problema, hueco.id, modos.opciones_banco, rng)
        return problema

    def banco(
        self, problema: ProblemaExpresion, hueco_id: str, cantidad: int, rng: random.Random
    ) -> list[OpcionBanco]:
        hueco = problema.huecos[hueco_id]
        if not isinstance(hueco, HuecoNumero):
            raise TypeError("El banco solo se arma para huecos numéricos")
        return armar_banco(
            correcta=hueco.correcta,
            distractores=distractores(self.reglas_error(), problema, hueco_id),
            cantidad=cantidad,
            rng=rng,
            es_valido=self.es_valido,
            paso=self.paso_cercano,
        )

    def clasificar_error(self, problema: Problema, hueco_id: str, valor: Any) -> str:
        """Código de la regla de error que explica la respuesta, o NO_CLASIFICADO. En la forma de
        ordenar, el hueco es "orden" y el valor la lista que dejó el estudiante (fase 5b)."""
        return clasificar(self.reglas_error(), problema, hueco_id, valor)

    def corregir(self, problema: Problema, respuestas: Any) -> ResultadoValidacion:
        """Valida las respuestas (lanza RespuestaMalFormada) y clasifica cada hueco incorrecto."""
        resultado = validar(problema, respuestas)
        for r in resultado.huecos.values():
            if not r.correcto:
                r.error = self.clasificar_error(problema, r.hueco_id, r.valor)
        return resultado

    def texto_pista(self, problema: Problema, nivel: int) -> str:
        if nivel not in NIVELES_PISTA:
            raise ValueError("El nivel de pista es 1, 2 o 3")
        return self.pista(problema, nivel)
