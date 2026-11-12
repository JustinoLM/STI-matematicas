"""
Regla de dominio por lección (docs/DISENO_MODULAR.md, sección 1 → Dominio por lección).

Lógica pura: recibe el estado y los resultados, devuelve el estado nuevo. Los valores salen de
ParametrosNucleo (provisionales, por validar con especialistas).

Resultado de un problema: es **acierto** si se resolvió al primer intento sin la pista de
nivel 3. Los problemas de la zona de extensión no cuentan (su progreso va aparte).

Estados: no iniciado (sin fila) → en progreso → dominado. El diagnóstico (fase 7) puede marcar
"dominado provisional".

- **Dominar:** al menos `umbral_dominio` de aciertos en los últimos `ventana_dominio` problemas,
  que deben abarcar `dias_distintos_dominio` o más días distintos (fecha de Panamá).
- **Repaso:** una lección dominada sin practicar durante `dias_para_repaso` días queda con el
  repaso vencido. El primer problema después abre una ventana de repaso con los
  `ventana_repaso` primeros problemas. Al completarla: con menos de `umbral_repaso` vuelve a
  "en progreso"; si no, sigue dominada y el repaso queda aprobado.
- **Dominio provisional:** se trata como un repaso desde el primer problema. Con menos de
  `umbral_repaso` en la ventana se retira (vuelve a "en progreso"); se confirma (pasa a
  "dominado") cuando cumple la regla absoluta.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from typing import Optional, Sequence

from app.models.nucleo import (
    DOMINIO_DOMINADO,
    DOMINIO_EN_PROGRESO,
    DOMINIO_PROVISIONAL,
    NO_INICIADO,
)
from app.nucleo.parametros import ParametrosNucleo

# Eventos que devuelve evaluar()
EV_INICIADA = "iniciada"
EV_DOMINADA = "dominada"
EV_REPASO_APROBADO = "repaso_aprobado"
EV_REPASO_FALLIDO = "repaso_fallido"
EV_PROVISIONAL_RETIRADO = "provisional_retirado"


@dataclass(frozen=True)
class Resultado:
    acierto: bool
    fecha: datetime          # UTC sin zona, como el resto de la base


@dataclass(frozen=True)
class EstadoDominio:
    estado: str = NO_INICIADO
    fecha_dominio: Optional[datetime] = None
    ultima_practica: Optional[datetime] = None
    repaso_desde: Optional[datetime] = None


def fecha_local(momento: datetime, p: ParametrosNucleo) -> date:
    return (momento + timedelta(hours=p.desfase_horario_horas)).date()


def precision(resultados: Sequence[Resultado]) -> Optional[float]:
    if not resultados:
        return None
    return sum(r.acierto for r in resultados) / len(resultados)


def recientes(resultados: Sequence[Resultado], p: ParametrosNucleo) -> list[Resultado]:
    """Los últimos `ventana_dominio` resultados (los resultados van en orden cronológico)."""
    return list(resultados[-p.ventana_dominio:])


def cumple_regla_dominio(resultados: Sequence[Resultado], p: ParametrosNucleo) -> bool:
    ventana = recientes(resultados, p)
    if len(ventana) < p.ventana_dominio:
        return False
    if precision(ventana) < p.umbral_dominio:
        return False
    return len({fecha_local(r.fecha, p) for r in ventana}) >= p.dias_distintos_dominio


def repaso_vencido(e: EstadoDominio, ahora: datetime, p: ParametrosNucleo) -> bool:
    """¿La lección dominada lleva `dias_para_repaso` días o más sin practicarse?"""
    return (
        e.estado == DOMINIO_DOMINADO
        and e.repaso_desde is None
        and e.ultima_practica is not None
        and ahora - e.ultima_practica >= timedelta(days=p.dias_para_repaso)
    )


def repaso_pendiente(e: EstadoDominio, ahora: datetime, p: ParametrosNucleo) -> bool:
    """¿Hay que practicar la lección como repaso? (vencido, ventana abierta o provisional)."""
    if e.estado == DOMINIO_PROVISIONAL:
        return True
    return e.estado == DOMINIO_DOMINADO and (e.repaso_desde is not None or repaso_vencido(e, ahora, p))


def evaluar(
    e: EstadoDominio, resultados: Sequence[Resultado], p: ParametrosNucleo
) -> tuple[EstadoDominio, Optional[str]]:
    """Estado nuevo tras un problema terminado.

    `resultados` son todos los resultados de la lección en orden cronológico; el último es el
    que se acaba de terminar. `e` es el estado de antes de ese problema."""
    if not resultados:
        raise ValueError("evaluar() necesita al menos el resultado nuevo")
    nuevo = resultados[-1]
    evento: Optional[str] = None

    if e.estado == NO_INICIADO:
        e = EstadoDominio(estado=DOMINIO_EN_PROGRESO)
        evento = EV_INICIADA

    # Abrir la ventana de repaso: provisional desde el primer problema; dominado si venció
    if e.repaso_desde is None and (
        e.estado == DOMINIO_PROVISIONAL or repaso_vencido(e, nuevo.fecha, p)
    ):
        e = replace(e, repaso_desde=nuevo.fecha)

    # Cerrar la ventana de repaso cuando se completa
    if e.repaso_desde is not None and e.estado in (DOMINIO_DOMINADO, DOMINIO_PROVISIONAL):
        ventana = [r for r in resultados if r.fecha >= e.repaso_desde][:p.ventana_repaso]
        if len(ventana) == p.ventana_repaso and ventana[-1] is nuevo:   # se completó justo ahora
            if precision(ventana) < p.umbral_repaso:
                evento = EV_REPASO_FALLIDO if e.estado == DOMINIO_DOMINADO else EV_PROVISIONAL_RETIRADO
                e = replace(e, estado=DOMINIO_EN_PROGRESO, repaso_desde=None)
            elif e.estado == DOMINIO_DOMINADO:
                evento = EV_REPASO_APROBADO
                e = replace(e, repaso_desde=None)
            # Provisional aprobado: sigue provisional hasta cumplir la regla absoluta

    # Dominar o confirmar el dominio provisional
    if e.estado in (DOMINIO_EN_PROGRESO, DOMINIO_PROVISIONAL) and cumple_regla_dominio(resultados, p):
        e = replace(e, estado=DOMINIO_DOMINADO, fecha_dominio=nuevo.fecha, repaso_desde=None)
        evento = EV_DOMINADA

    return replace(e, ultima_practica=nuevo.fecha), evento
