"""
Reemplaza el componente Microsoft.DataConvert del Data Flow
"TBL_CONTACTOS_AUTORIZADOS_CHILE":
  - Columnas de texto: se mantienen wstr, solo se recorta espacio.
  - "Cargo", "Teléfono", "Móvil", "Última modificación por": tienen
    errorRowDisposition/truncationRowDisposition="IgnoreFailure" en el
    .dtsx -- si el valor excede su ancho, SSIS lo trunca en silencio y
    sigue. Confirmado con datos reales de producción: un TELÉFONO de
    21 caracteres reventó la carga en SQL Server (ancho real 20) antes de
    que se replicara este truncamiento.
  - "Acceso a Portal Platino" / "Representante legal": Data Convert las pasa
    a r4 (float), pero la columna destino real es i4 (entero) -- acá se
    castea directo a entero anulable (Int64), incluye "False"/"True" porque
    algunas filas del reporte real vienen como texto en vez de 0/1.
  - Fechas: formato real confirmado en el CSV es DD-MM-AAAA (ej. 04-12-2017).

Al final renombra a los nombres de columna de
[CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE] (ver columns.py).
"""
from __future__ import annotations

import logging

import pandas as pd

from contactos.columns import (
    ANCHOS_MAXIMOS_TEXTO,
    COLUMNAS_ENTERAS,
    COLUMNAS_FECHA,
    COLUMNAS_TEXTO,
    COLUMNAS_TRUNCAR_SILENCIOSO,
    MAPEO_DESTINO,
)

logger = logging.getLogger(__name__)

_BOOL_A_ENTERO = {"true": 1, "false": 0, "1": 1, "0": 0}


def _a_entero_anulable(serie: pd.Series) -> pd.Series:
    normalizado = serie.str.strip().str.lower().map(_BOOL_A_ENTERO)
    normalizado = normalizado.fillna(pd.to_numeric(serie, errors="coerce"))
    return normalizado.astype("Int64")


def transform_contactos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Data Convert -> texto (wstr). dtype "string" (nullable), NO astype(str):
    # astype(str) convierte NaN en el texto literal "nan".
    for col in COLUMNAS_TEXTO:
        df[col] = df[col].astype("string").str.strip()

    # IgnoreFailure: truncar en silencio, igual que el Data Convert original.
    for col in COLUMNAS_TRUNCAR_SILENCIOSO:
        ancho = ANCHOS_MAXIMOS_TEXTO[col]
        muy_largo = df[col].str.len() > ancho
        if muy_largo.any():
            logger.warning(
                "%d fila(s) con '%s' > %d caracteres -- se truncan (IgnoreFailure en el .dtsx original).",
                int(muy_largo.sum()),
                col,
                ancho,
            )
        df[col] = df[col].str.slice(0, ancho)

    for col in COLUMNAS_ENTERAS:
        df[col] = _a_entero_anulable(df[col])

    for col in COLUMNAS_FECHA:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="raise").dt.date

    df = df.rename(columns=MAPEO_DESTINO)

    logger.info("Transformación de contactos completada (%d filas).", len(df))
    return df
