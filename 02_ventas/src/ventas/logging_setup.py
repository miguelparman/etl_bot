"""Configuracion de logging (archivo + consola).

- Archivo ('ventas.log'): TODO, INFO en adelante -- traza completa de cada
  paso y avisos de calidad de datos (filas corregidas/truncadas/vaciadas).
- Consola: solo los hitos marcados con 'extra=CONSOLA' y los errores. Los
  avisos (WARNING) no se imprimen uno a uno: se cuentan y 'resumen_avisos()'
  devuelve una sola linea con el total, apuntando al archivo.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

NOMBRE_LOGGER = "ventas"

# Pasar como 'extra=CONSOLA' en un logger.info(...) para que tambien salga por consola.
CONSOLA = {"consola": True}


class _FiltroConsola(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR or getattr(record, "consola", False)


class _ContadorAvisos(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.total = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.WARNING:
            self.total += 1


_contador = _ContadorAvisos()
_log_file: Path | None = None


def configurar_logging(log_file: Path) -> logging.Logger:
    global _log_file
    _log_file = Path(log_file)

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    consola.addFilter(_FiltroConsola())

    archivo = logging.FileHandler(log_file, encoding="utf-8")
    archivo.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(level=logging.INFO, handlers=[archivo, consola, _contador])
    return logging.getLogger(NOMBRE_LOGGER)


def resumen_avisos() -> str | None:
    """Linea para consola con el total de avisos, o None si no hubo."""
    if _contador.total == 0:
        return None
    nombre = _log_file.name if _log_file else "el log"
    return f"{_contador.total} aviso(s) de calidad de datos, detalle en '{nombre}'."
