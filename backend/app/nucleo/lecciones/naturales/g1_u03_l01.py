"""
g1-u03-l01 "Sumemos de forma horizontal" (1.º grado, unidad 3: suma y resta hasta 10).

Generador de referencia del núcleo.

- Rango: sumandos de 1 a 9 y total de 2 a 10 (sin 0). Se elige primero el total y luego el
  primer sumando, así todos los totales salen con la misma frecuencia.
- Con el signo visible: `a + b = _` (hueco numérico "resultado").
- Con el signo oculto: `a _ b = c` (hueco de opción "operador": + o −). Como b nunca es 0,
  solo "+" es correcto.
- Íconos: una cantidad por sumando.
"""

import random
from decimal import Decimal

from app.nucleo.generador import GeneradorLeccion
from app.nucleo.lecciones.naturales.reglas import (
    HUECO_OPERADOR,
    HUECO_RESULTADO,
    OPCION_SUMA,
    OPCIONES_SUMA_RESTA,
    REGLAS_SUMA,
)
from app.nucleo.modos import ModosProblema
from app.nucleo.problema import (
    HuecoNumero,
    HuecoOpcion,
    Numero,
    Problema,
    ProblemaExpresion,
    RefHueco,
    Simbolo,
)


class SumemosHorizontal(GeneradorLeccion):
    leccion_id = "g1-u03-l01"
    caminos = ("naturales.suma",)
    version = 1
    admite_signo_oculto = True
    admite_iconos = True

    SUMANDO_MIN = 1
    TOTAL_MIN = 2
    TOTAL_MAX = 10

    def generar(self, rng: random.Random, modos: ModosProblema) -> Problema:
        total = rng.randint(self.TOTAL_MIN, self.TOTAL_MAX)
        a = rng.randint(self.SUMANDO_MIN, total - self.SUMANDO_MIN)
        b = total - a

        if modos.mostrar_signo:
            segmentos = [Numero(Decimal(a)), Simbolo("+"), Numero(Decimal(b)), Simbolo("="),
                         RefHueco(HUECO_RESULTADO)]
            huecos = {HUECO_RESULTADO: HuecoNumero(HUECO_RESULTADO, Decimal(total))}
        else:
            segmentos = [Numero(Decimal(a)), RefHueco(HUECO_OPERADOR), Numero(Decimal(b)),
                         Simbolo("="), Numero(Decimal(total))]
            huecos = {HUECO_OPERADOR: HuecoOpcion(HUECO_OPERADOR, OPCIONES_SUMA_RESTA, OPCION_SUMA.id)}

        return ProblemaExpresion(
            leccion_id=self.leccion_id,
            generador_version=self.version,
            segmentos=segmentos,
            huecos=huecos,
            modos=modos,
            datos={"sumandos": [a, b]},
            iconos=[a, b] if modos.mostrar_iconos else None,
        )

    def reglas_error(self):
        return REGLAS_SUMA

    def en_rango(self, problema: Problema) -> bool:
        a, b = problema.datos["sumandos"]
        if not (a >= self.SUMANDO_MIN and b >= self.SUMANDO_MIN and self.TOTAL_MIN <= a + b <= self.TOTAL_MAX):
            return False
        numeros = [s.valor for s in problema.segmentos if isinstance(s, Numero)]
        if problema.modos.mostrar_signo:
            return numeros == [a, b] and problema.huecos[HUECO_RESULTADO].correcta == a + b
        return numeros == [a, b, a + b]

    def es_valido(self, valor: Decimal) -> bool:
        return valor >= 0 and valor == valor.to_integral_value()

    def pista(self, problema: Problema, nivel: int) -> str:
        a, b = problema.datos["sumandos"]
        total = a + b
        if not problema.modos.mostrar_signo:
            return {
                1: f"Mira el resultado: ¿es más que {a} o menos que {a}?",
                2: f"{total} es más que {a}. Cuando juntamos cosas, tenemos más.",
                3: f"Si juntas {a} y {b}, tienes {total}. ¿Qué signo usamos para juntar?",
            }[nivel]
        if nivel == 1:
            return f"Sumar es juntar: junta los {a} y los {b}, y cuenta cuántos hay en total."
        if nivel == 2:
            return f"Empieza en {a} y cuenta {b} más con los dedos."
        intermedios = ", ".join(str(n) for n in range(a + 1, total))
        if intermedios:
            return f"Cuenta desde {a}: {intermedios}… ¿qué número sigue?"
        return f"¿Qué número viene después del {a}?"
