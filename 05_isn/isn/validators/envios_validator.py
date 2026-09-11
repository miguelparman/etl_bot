"""
Validación previa al casteo a entero de FECHA_EVENTO / "Número del caso" en
el Data Flow "TBL_ISN_ENVIOS_CONSOLIDADOS". El Data Convert original tiene
errorRowDisposition="FailComponent" en ambas columnas: si no castean, SSIS
frena todo el Data Flow. Se replica ese "fail fast" acá, con un mensaje que
dice exactamente qué filas fallarían.
"""
from __future__ import annotations

import pandas as pd

from isn.columns import COLUMNAS_ENVIOS_CONSOLIDADO, COLUMNAS_ENVIOS_CONSOLIDADO_ENTERAS


def validar_envios_consolidado(df: pd.DataFrame) -> None:
    faltantes = [c for c in COLUMNAS_ENVIOS_CONSOLIDADO if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas esperadas en TBL_ISN_CALIDAD: {faltantes}")

    for col in COLUMNAS_ENVIOS_CONSOLIDADO_ENTERAS:
        no_numerico = df[col].notna() & ~df[col].astype(str).str.strip().str.fullmatch(r"-?\d+", na=False)
        if no_numerico.any():
            filas = df.index[no_numerico].tolist()[:5]
            raise ValueError(
                f"La columna '{col}' tiene valores no enteros (equivalente al FailComponent "
                f"del Data Convert de SSIS en el Data Flow TBL_ISN_ENVIOS_CONSOLIDADOS). "
                f"Ejemplo de filas: {filas}"
            )
