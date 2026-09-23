"""Configuracion de logging (archivo + consola). Un archivo de log por
corrida ('logs/correos_<timestamp>.log'), no uno unico que crece sin limite
-- mismo patron que 05_isn/main.py."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

NOMBRE_LOGGER = "correos"


def configurar_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"correos_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(NOMBRE_LOGGER)
