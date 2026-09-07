"""
Reemplaza los componentes Microsoft.ExcelSource del Data Flow.
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def read_excel_sheet(path: str, sheet_name: str) -> pd.DataFrame:
    """
    Lee una hoja de Excel completa.

    Nota: en el .dtsx los OpenRowset son 'DB$' y 'DB_DETRACTOR$' (el '$' es la
    convención interna de SSIS para nombrar hojas). Aquí se usa el nombre sin '$'.
    """
    logger.info("Leyendo Excel: %s [hoja=%s]", path, sheet_name)
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    logger.info("Filas leídas: %d, columnas: %s", len(df), list(df.columns))
    return df
