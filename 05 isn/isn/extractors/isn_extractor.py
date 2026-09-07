"""
Reemplaza los Microsoft.OLEDBSource de SSIS_CL_ISN.dtsx que leen desde la
propia base CL_ISN (no son Execute SQL Task, son orígenes de Data Flow):
- 'TBL_ISN_CALIDAD (local)' del Data Flow 'TBL_ISN_ENVIOS_CONSOLIDADOS'
  (AccessMode=0, tabla completa, sin SQL).
- 'TBL_ISN' del Data Flow 'EXPORT CSV' (AccessMode=2, SQL explícito).
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import settings
from db import get_engine
from isn.columns import COLUMNAS_ENVIOS_CONSOLIDADO, TABLA_ISN_CALIDAD

logger = logging.getLogger(__name__)

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def leer_tbl_isn_calidad() -> pd.DataFrame:
    """Origen del Data Flow 'TBL_ISN_ENVIOS_CONSOLIDADOS': toda la tabla TBL_ISN_CALIDAD."""
    engine = get_engine(settings.db_database_isn)
    columnas = ", ".join(f"[{c}]" for c in COLUMNAS_ENVIOS_CONSOLIDADO)
    logger.info("Leyendo %s desde %s", TABLA_ISN_CALIDAD, settings.db_database_isn)
    df = pd.read_sql(f"SELECT {columnas} FROM [dbo].[{TABLA_ISN_CALIDAD}]", engine)
    logger.info("Filas leídas de %s: %d", TABLA_ISN_CALIDAD, len(df))
    return df


def leer_tbl_isn_para_export() -> pd.DataFrame:
    """Origen del Data Flow 'EXPORT CSV': SELECT explícito sobre TBL_ISN."""
    sql = (_SQL_DIR / "select_tbl_isn_export.sql").read_text(encoding="utf-8")
    engine = get_engine(settings.db_database_isn)
    logger.info("Leyendo TBL_ISN para exportar a CSV")
    df = pd.read_sql(sql, engine)
    logger.info("Filas leídas de TBL_ISN: %d", len(df))
    return df
