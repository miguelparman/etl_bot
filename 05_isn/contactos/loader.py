"""
Reemplaza los Execute SQL Task (TRUNCATE / UPDATE) y OLE DB Destination del
paquete SSIS_CL_ISN_Contactos.dtsx.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from common.sql_loader import load_dataframe, truncate_table
from config import settings
from contactos.columns import TABLA_DESTINO, TABLA_NUMEROS
from db import run_sql_file

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent / "sql"
_DATABASE = settings.db_database_analisis


def truncar_contactos() -> None:
    truncate_table(_DATABASE, TABLA_DESTINO)


def cargar_contactos(df: pd.DataFrame) -> int:
    return load_dataframe(_DATABASE, df, TABLA_DESTINO)


def limpiar_telefonos() -> None:
    """Tarea 'UPDATE \"_0\"': quita el sufijo '.0' de MÓVIL/TELÉFONO."""
    run_sql_file(_DATABASE, _SQL_DIR / "update_limpiar_telefonos.sql")


def truncar_numeros() -> None:
    truncate_table(_DATABASE, TABLA_NUMEROS)


def cargar_numeros(df: pd.DataFrame) -> int:
    return load_dataframe(_DATABASE, df, TABLA_NUMEROS)
