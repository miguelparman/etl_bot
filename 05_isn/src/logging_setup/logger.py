"""Configuracion de logging del ETL (equivalente a los logs de ejecucion de SSIS)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ssis_cl_isn")
    logger.setLevel(level.upper())
    logger.propagate = False
    if logger.handlers:
        return logger  # ya configurado (evita handlers duplicados en tests/reimports)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(
        log_dir / "ssis_cl_isn.log", encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
