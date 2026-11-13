"""
Pistas de las lecciones de numeración (fase 5b). Nivel 1: estrategia; 2: paso a paso; 3: casi la
respuesta. Siguen las estrategias de Panamáticas 1.º: contar señalando uno a uno, agrupar de 10
en 10, descomponer en decenas y unidades, ubicar en la semirrecta desde la decena completa.
"""

from app.nucleo.lecciones.naturales.numeracion import (
    COMPARAR,
    COMPONER,
    CONTAR,
    DECENAS,
    DESCOMPONER,
    FORMAR,
    FORMAR_FALTANTE,
    GRUPOS,
    LEER,
    NOMBRE,
    ORDENAR,
    SECUENCIA,
    UBICAR,
    indice_termino,
)
from app.nucleo.problema import Problema


def _contar(n: int) -> dict[int, str]:
    if n == 0:
        return {1: "Mira bien el recuadro: ¿hay algo dentro?",
                2: "Si no hay ningún objeto, decimos que hay cero.",
                3: "No hay ninguno. ¿Qué número dice «ninguno»?"}
    if n > 10:
        d, u = divmod(n, 10)
        return {1: "Cada barra tiene 10. Cuenta las barras de 10 en 10.",
                2: f"Hay {d} {'barra' if d == 1 else 'barras'}: {', '.join(str(10 * k) for k in range(1, d + 1))}."
                   + (" Luego sigue con las sueltas." if u else ""),
                3: f"{10 * d} y {u} sueltas. ¿Qué número forman?" if u else f"Son {d} barras de 10. ¿Cuántos son?"}
    return {1: "Toca cada objeto con el dedo mientras cuentas.",
            2: "Cuenta despacio: uno, dos, tres… un número por cada objeto.",
            3: "Hay una fila de 5. Sigue contando desde 5." if n > 5 else "Cuenta otra vez, sin saltarte ninguno."}


def pista_numeracion(p: Problema, nivel: int) -> str:
    d = p.datos
    forma = d["forma"]
    if forma == CONTAR:
        return _contar(d["n"])[nivel]
    if forma == NOMBRE:
        n = d["n"]
        if n >= 20 and n % 10:
            return {1: "Primero se dice la decena y luego las unidades.",
                    2: f"«{n // 10 * 10}» se escribe con la cifra {n // 10} delante.",
                    3: f"La decena es {n // 10 * 10} y las unidades {n % 10}. ¿Qué número forman?"}[nivel]
        return {1: "Lee el nombre en voz alta, despacio.",
                2: "Cuenta con los dedos hasta llegar a ese número.",
                3: f"Está entre {max(n - 1, 0)} y {n + 1}." if n else "Es el número de «ninguno»."}[nivel]
    if forma == FORMAR:
        a, b = d["numeros"]
        return {1: "Junta los dos números y cuenta cuántos hay en total.",
                2: f"Empieza en {a} y cuenta {b} más.",
                3: f"Cuenta desde {a}: {', '.join(str(a + k) for k in range(1, b))}… ¿qué número sigue?"
                   if b > 1 else f"¿Qué número viene después del {a}?"}[nivel]
    if forma == FORMAR_FALTANTE:
        conocido, faltante = d["numeros"]
        total = conocido + faltante
        return {1: f"Tienes {conocido}. ¿Cuántos faltan para llegar a {total}?",
                2: f"Cuenta desde {conocido} hasta {total} con los dedos.",
                3: f"De {conocido} a {total}: ¿cuántos números contaste?"}[nivel]
    if forma == SECUENCIA:
        salto = d["salto"]
        paso = abs(salto)
        sentido = "hacia adelante" if salto > 0 else "hacia atrás"
        hueco = next(iter(p.huecos)) if hasattr(p, "huecos") else None
        i = indice_termino(hueco) if hueco else None
        previo = d["inicio"] + salto * (i - 1) if i else d["inicio"]
        return {1: f"Los números van de {paso} en {paso}, {sentido}.",
                2: f"Mira el número antes del espacio: {previo}." if i else "Mira el primer número.",
                3: f"{previo} {'+' if salto > 0 else '−'} {paso}. ¿Qué número es?"}[nivel]
    if forma == GRUPOS:
        g = d["grupos"]
        if d["faltante"]:
            return {1: "Cuenta de 10 en 10 hasta llegar al número.",
                    2: f"10, 20, 30… ¿cuántas veces dijiste un número hasta llegar a {10 * g}?",
                    3: f"{10 * g} tiene la cifra {g} en las decenas."}[nivel]
        return {1: "Cuenta de 10 en 10: un número por cada grupo.",
                2: f"10, 20, 30… cuenta {g} {'vez' if g == 1 else 'veces'}.",
                3: f"{g} grupos de 10 son {g} decenas. ¿Qué número es?"}[nivel]
    if forma in (DECENAS, DESCOMPONER):
        n = d["n"]
        return {1: "Las decenas son los grupos de 10; las unidades, los que sobran.",
                2: f"En {n}, la primera cifra dice cuántas decenas hay.",
                3: f"{n} tiene {n // 10} decenas, que son {n // 10 * 10}, y {n % 10} unidades."
                   if forma == DESCOMPONER else f"{n}: la cifra {n // 10} son las decenas."}[nivel]
    if forma == COMPONER:
        n = d["n"]
        return {1: "Las decenas se escriben primero y las unidades después.",
                2: f"{n // 10} decenas son {n // 10 * 10}.",
                3: f"{n // 10 * 10} y {n % 10} forman… ¿qué número?"}[nivel]
    if forma == COMPARAR:
        a, b = d["a"], d["b"]
        if a // 10 == b // 10:
            return {1: "Mira primero las decenas, luego las unidades.",
                    2: "Las decenas son iguales: compara las unidades.",
                    3: f"Compara {a % 10} y {b % 10}. El símbolo abre su boca hacia el mayor."}[nivel]
        return {1: "Mira primero las decenas: el que tiene más decenas es mayor.",
                2: f"{a} tiene {a // 10} decenas y {b} tiene {b // 10}.",
                3: "El símbolo abre su boca hacia el número mayor."}[nivel]
    if forma == LEER:
        n = d["n"]
        return {1: "Busca el número escrito más cercano a la flecha.",
                2: f"La flecha está después del {n // 10 * 10}." if n % 10 and d["hasta"] - d["desde"] > 20
                   else "Cuenta las marcas desde un número escrito.",
                3: f"Desde el {n // 10 * 10}, cuenta {n % 10} marcas hacia la derecha."
                   if n % 10 else f"Está justo en una decena: {n // 10} grupos de 10."}[nivel]
    if forma == UBICAR:
        n = d["n"]
        return {1: f"Separa el {n} en decenas y unidades.",
                2: f"{n} es {n // 10 * 10} y {n % 10}. Busca el {n // 10 * 10} en la semirrecta.",
                3: f"Desde el {n // 10 * 10}, cuenta {n % 10} marcas hacia la derecha."}[nivel]
    if forma == ORDENAR:
        menor = "de menor a mayor" if d["ascendente"] else "de mayor a menor"
        return {1: f"Ordena {menor}, como en la semirrecta.",
                2: "Compara primero las decenas: el que tiene menos decenas es menor.",
                3: f"Busca el número {'más pequeño' if d['ascendente'] else 'más grande'} y ponlo primero."}[nivel]
    raise ValueError(f"Forma desconocida: {forma}")
