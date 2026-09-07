"""
Logging centralizado.

- Salida simultanea a consola y a un archivo diario en logs/.
- Un filtro redacta cualquier valor sensible conocido (CLIENT_SECRET,
  password de Salesforce, access tokens) si por error terminara en un
  mensaje de log, como defensa adicional a "nunca loguear secretos".
- Al ejecutarse con pythonw.exe (sin consola, pensado para tareas
  programadas desatendidas) sys.stdout/sys.stderr son None; en ese caso no
  se agrega el handler de consola y se registra solo en archivo.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime

from app.config import settings

_REDACTED = "***REDACTED***"


class SensitiveDataFilter(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self._secrets:
            if secret in message:
                message = message.replace(secret, _REDACTED)
        record.msg = message
        record.args = ()
        return True


def setup_logger(name: str = "sf_sharepoint_bot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # ya configurado

    logger.setLevel(logging.INFO)

    # En Windows, la consola puede estar en una codificacion (p.ej. cp1252)
    # que no soporta caracteres como los usados en el resumen final
    # (checkmarks Unicode). Se fuerza UTF-8 en stdout/stderr para evitar un
    # UnicodeEncodeError a mitad de una ejecucion larga.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sensitive_filter = SensitiveDataFilter(settings.sensitive_values())

    log_file = settings.logs_dir / f"bot_{datetime.now():%Y%m%d}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)
    logger.addHandler(file_handler)

    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        logger.addHandler(console_handler)

    return logger


log = setup_logger()
