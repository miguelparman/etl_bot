"""
Reemplaza Microsoft.FlatFileSource "Reporte_isn_aux_contacto_v2" del Data
Flow "TBL_ISN_AUX_CONTACTO 1\\TBL_ISN_AUX_CONTACTO".
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import settings
from isn.columns import COLUMNAS_AUX_CONTACTO

logger = logging.getLogger(__name__)


def leer_aux_contacto(path: Path | None = None) -> pd.DataFrame:
    path = path or settings.csv_isn_aux_contacto_path
    logger.info("Leyendo CSV auxiliar de contacto: %s", path)
    df = pd.read_csv(
        path,
        sep=",",
        encoding=settings.csv_isn_encoding,
        quotechar='"',
        header=0,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )
    if len(df.columns) != len(COLUMNAS_AUX_CONTACTO):
        raise ValueError(
            f"Se esperaban {len(COLUMNAS_AUX_CONTACTO)} columnas en {path}, se encontraron {len(df.columns)}: "
            f"{list(df.columns)}"
        )
    df.columns = COLUMNAS_AUX_CONTACTO
    for col in COLUMNAS_AUX_CONTACTO:
        df[col] = df[col].astype("string").str.strip()
    logger.info("Filas leídas (aux contacto): %d", len(df))
    return df
