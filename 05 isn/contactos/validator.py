"""
Validación previa a la transformación/carga. SSIS no tenía un paso de
validación explícito -- las validaciones de tipo ocurrían implícitamente en
el componente Data Convert (con errorRowDisposition="FailComponent": una
fila que no castea, revienta todo el Data Flow). Acá se hace explícito y se
falla temprano con un mensaje claro, en vez de que el INSERT reviente más
adelante con un error de SQL Server/pyodbc menos claro.
"""
from __future__ import annotations

import logging

import pandas as pd

from contactos.columns import ANCHOS_MAXIMOS_TEXTO, COLUMNAS_ENTERAS, COLUMNAS_FALLAR_SI_EXCEDE, COLUMNAS_ORIGEN

logger = logging.getLogger(__name__)


def validar_contactos(df: pd.DataFrame) -> None:
    faltantes = [c for c in COLUMNAS_ORIGEN if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas esperadas en el CSV de contactos: {faltantes}")

    if df.empty:
        raise ValueError("El CSV de contactos no trae filas.")

    # Acepta numérico ("1"/"0") -- lo único visto en el archivo real -- o
    # texto "True"/"False", por si alguna exportación futura de Salesforce
    # trae el booleano como texto (mismo conjunto que castea el transformer).
    patron_valido = r"-?\d+(\.\d+)?|true|false"
    for col in COLUMNAS_ENTERAS:
        valor = df[col].str.strip().str.lower()
        no_valido = df[col].notna() & ~valor.str.fullmatch(patron_valido, na=False)
        if no_valido.any():
            filas = df.index[no_valido].tolist()[:5]
            raise ValueError(
                f"La columna '{col}' tiene valores no numéricos ni True/False (equivalente al "
                f"FailComponent del Data Convert de SSIS). Ejemplo de filas: {filas}"
            )

    # Estas columnas tienen errorRowDisposition/truncationRowDisposition=
    # "FailComponent" en el .dtsx (a diferencia de Cargo/Teléfono/Móvil/
    # Última modificación por, que son IgnoreFailure y se truncan en
    # transformer.py): si un valor excede su ancho real, SSIS frenaba todo
    # el Data Flow -- acá se rechaza el archivo completo con el mismo
    # criterio, en vez de dejar que reviente más adelante en el INSERT.
    for col in COLUMNAS_FALLAR_SI_EXCEDE:
        ancho = ANCHOS_MAXIMOS_TEXTO[col]
        muy_largo = df[col].str.len() > ancho
        if muy_largo.any():
            filas = df.index[muy_largo].tolist()[:5]
            raise ValueError(
                f"La columna '{col}' tiene valores de más de {ancho} caracteres (equivalente al "
                f"FailComponent del Data Convert de SSIS). Ejemplo de filas: {filas}"
            )

    logger.info("Validación de contactos OK (%d filas).", len(df))
