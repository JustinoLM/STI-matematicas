"""Servicios del núcleo con acceso a la base: habilitación del profesor y práctica del estudiante."""

from app.services.school_service import ErrorSalon


class RespuestaInvalida(ErrorSalon):
    """La respuesta no tiene la forma que exige el problema (no cuenta como intento)."""
    status_code = 422
    codigo = "RESPUESTA_INVALIDA"


class Prohibido(ErrorSalon):
    status_code = 403


class SaldoInsuficiente(ErrorSalon):
    status_code = 402
