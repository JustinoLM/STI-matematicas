"""
Fechas y horas del sistema en un solo lugar (fase 7a).

- **Guardado:** todas las columnas `DateTime` guardan la hora UTC sin zona (`ahora_utc()`).
  No se migran datos: la convención ya era esa en toda la base.
- **API:** las horas salen siempre con zona (`2026-11-15T04:30:00Z`). Los esquemas usan el tipo
  `FechaHora`; las respuestas armadas como diccionarios pasan por el codificador de FastAPI, que
  `registrar_codificador()` ajusta al arrancar. Al recibir una hora con zona se convierte a UTC.
- **Reglas por día** (dominio, racha, repaso, trimestre vigente, caché diaria): usan la fecha de
  la zona del colegio (`ZONA_HORARIA`, por defecto America/Panama), con `fecha_local()` en Python
  y `dia_local_sql()` en las consultas.
- **Reloj fijo para probar:** en desarrollo, `STI_RELOJ_FIJO=2026-11-15T04:30:00Z` fija la hora del
  backend (para revisar fronteras de día). En producción se ignora.
"""

import logging
import os
from datetime import date, datetime, timezone
from typing import Annotated, Optional

from pydantic import AfterValidator, PlainSerializer
from sqlalchemy import Date, cast, func, literal_column
from zoneinfo import ZoneInfo

from app.core.config import settings

logger = logging.getLogger(__name__)

ZONA = ZoneInfo(settings.ZONA_HORARIA)


def _reloj_fijo() -> Optional[datetime]:
    crudo = os.environ.get("STI_RELOJ_FIJO", "").strip()
    if not crudo or settings.ENVIRONMENT == "production":
        return None
    try:
        return a_utc_sin_zona(datetime.fromisoformat(crudo.replace("Z", "+00:00")))
    except ValueError:
        logger.warning("STI_RELOJ_FIJO inválido: %r; se usa la hora real", crudo)
        return None


def ahora_utc() -> datetime:
    """Hora actual en UTC sin zona, como se guarda en la base."""
    return _reloj_fijo() or datetime.now(timezone.utc).replace(tzinfo=None)


def a_utc_sin_zona(momento: datetime) -> datetime:
    """Una hora con zona pasa a UTC sin zona; una sin zona se toma como UTC."""
    if momento.tzinfo is None:
        return momento
    return momento.astimezone(timezone.utc).replace(tzinfo=None)


def fecha_local(momento: datetime) -> date:
    """Fecha del colegio para una hora UTC sin zona (o con zona)."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(ZONA).date()


def hoy_local() -> date:
    return fecha_local(ahora_utc())


def inicio_dia_local_utc(dia: date) -> datetime:
    """Primer instante del día del colegio, en UTC sin zona (para filtros `>=`)."""
    return a_utc_sin_zona(datetime(dia.year, dia.month, dia.day, tzinfo=ZONA))


def _literal_sql(texto: str):
    # Literal (no parámetro): así el mismo día sirve en el SELECT y en el GROUP BY.
    return literal_column("'" + texto.replace("'", "''") + "'")


def dia_local_sql(columna):
    """Expresión SQL con la fecha del colegio de una columna UTC sin zona."""
    return cast(func.timezone(_literal_sql(settings.ZONA_HORARIA), func.timezone(_literal_sql("UTC"), columna)), Date)


def a_iso_utc(momento: datetime) -> str:
    """ISO 8601 en UTC con «Z». Una hora sin zona se toma como UTC."""
    return a_utc_sin_zona(momento).isoformat() + "Z"


# Tipo para los esquemas: valida entradas con zona a UTC sin zona y serializa con «Z».
FechaHora = Annotated[
    datetime,
    AfterValidator(a_utc_sin_zona),
    PlainSerializer(a_iso_utc, return_type=str, when_used="json"),
]


def registrar_codificador() -> None:
    """Las respuestas que no pasan por un esquema (diccionarios) también llevan «Z»."""
    from fastapi.encoders import ENCODERS_BY_TYPE

    ENCODERS_BY_TYPE[datetime] = a_iso_utc
