"""
Configuración de registros (logging) de la aplicación.

- Producción (`LOG_FORMAT=json`, valor por defecto fuera de desarrollo): una línea JSON por
  registro, con campos propios (`method`, `path`, `status`, `duration_ms`, `request_id`...).
- Desarrollo (`LOG_FORMAT=text`): línea legible.
"""

import json
import logging
import sys
from datetime import datetime, timezone

# Atributos estándar de LogRecord: lo demás que traiga un registro (`extra=`) se agrega al JSON
_ATRIBUTOS_ESTANDAR = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Formatea cada registro como un objeto JSON en una sola línea."""

    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for clave, valor in record.__dict__.items():
            if clave not in _ATRIBUTOS_ESTANDAR and not clave.startswith("_"):
                datos[clave] = valor
        if record.exc_info:
            datos["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging(formato: str = "text", nivel: str = "INFO") -> None:
    """Configura el logger raíz; se puede llamar varias veces."""
    handler = logging.StreamHandler(sys.stdout)
    if formato == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel.upper())
    # El registro de acceso lo hace el middleware de la aplicación (con duración e id)
    logging.getLogger("uvicorn.access").disabled = True
