"""Capa de infraestructura: configuracion de logging a archivo + consola."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def configurar_logger(log_dir: Path, nombre: str = "bot_portal_comercial") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"bot_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(nombre)
