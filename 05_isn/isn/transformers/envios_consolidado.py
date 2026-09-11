"""
Reemplaza el componente Microsoft.DataConvert del Data Flow
"TBL_ISN_ENVIOS_CONSOLIDADOS": todas las columnas viajan 1:1, salvo
FECHA_EVENTO y "Número del caso" que se castean de texto a entero (i4).
"""
from __future__ import annotations

import logging

import pandas as pd

from isn.columns import COLUMNAS_ENVIOS_CONSOLIDADO_ENTERAS

logger = logging.getLogger(__name__)


def transform_envios_consolidado(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in COLUMNAS_ENVIOS_CONSOLIDADO_ENTERAS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("Int64")
    logger.info("Transformación de TBL_ISN_ENVIOS_CONSOLIDADO completada (%d filas).", len(df))
    return df
