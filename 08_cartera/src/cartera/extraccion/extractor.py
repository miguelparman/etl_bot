"""Extraccion: Data Flow 'CL_TEMPORALES TBL_CARTERA' de CL_Proc_Carga_Cartera.dtsx,
componentes 'Origen de Excel' + 'Conversion de datos' + 'Columna derivada'
(el cuarto componente, el Destino OLE DB, es responsabilidad de carga/loader.py).

Solo conoce SpreadsheetReader (spreadsheet.py) y las reglas de saneo/tipado,
que son logica de negocio (los anchos de truncamiento y las columnas
descartadas son parte del proceso original, no un detalle tecnico de
lectura de archivos).
"""

from __future__ import annotations

import logging

import pandas as pd

import mappings
from exceptions import ExtraccionError
from models import Periodo
from spreadsheet import SpreadsheetReader

logger = logging.getLogger("cartera")


def extraer(reader: SpreadsheetReader, excel_path: str, periodo: Periodo) -> pd.DataFrame:
    df = _leer(reader, excel_path)
    df = _truncar(df)
    df = _agregar_periodo(df, periodo)
    return df[list(mappings.STAGING_INSERT_COLUMNS)]


def _leer(reader: SpreadsheetReader, excel_path: str) -> pd.DataFrame:
    try:
        df = reader.read_sheet(excel_path, mappings.EXCEL_SHEET)
    except Exception as exc:
        raise ExtraccionError(
            f"No se pudo leer el Excel '{excel_path}' (hoja '{mappings.EXCEL_SHEET}'): {exc}"
        ) from exc

    columnas_faltantes = set(mappings.EXCEL_COLUMNS) - set(df.columns)
    if columnas_faltantes:
        raise ExtraccionError(
            f"Faltan columnas esperadas en la hoja '{mappings.EXCEL_SHEET}': {sorted(columnas_faltantes)}"
        )

    logger.info("Excel leido: %s filas", len(df))
    df = df[list(mappings.EXCEL_COLUMNS)].copy()
    # Componente 'Conversion de datos': solo se crean columnas de salida
    # para las columnas que el paquete original propaga; RUTCLI y RUT10
    # se leen pero no llegan a ninguna parte.
    return df.drop(columns=list(mappings.EXCEL_COLUMNS_DESCARTADAS))


def _truncar(df: pd.DataFrame) -> pd.DataFrame:
    # Componente 'Conversion de datos': errorRowDisposition="FailComponent"
    # para todas las columnas salvo NOMCLI (IgnoreFailure). Un valor que
    # excede el ancho debe abortar la extraccion igual que en el .dtsx
    # original, no truncarse en silencio.
    try:
        df = df.copy()
        for columna, largo in mappings.TRUNCATION_LENGTHS.items():
            valores = df[columna].astype("string")
            if columna != mappings.TRUNCATION_TOLERANT_COLUMN:
                excede = valores.str.len() > largo
                if excede.any():
                    filas = df.index[excede].tolist()
                    raise ExtraccionError(
                        f"La columna '{columna}' excede el ancho de truncamiento "
                        f"({largo} caracteres) en las filas {filas}; el componente "
                        "'Conversion de datos' original aborta el Data Flow en este caso "
                        "(errorRowDisposition=FailComponent)."
                    )
            df[columna] = valores.str.slice(0, largo)
        return df
    except ExtraccionError:
        raise
    except Exception as exc:
        raise ExtraccionError(f"No se pudieron tipar/truncar las columnas: {exc}") from exc


def _agregar_periodo(df: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
    # Componente 'Columna derivada': Fecha_Inicio = @[User::Fecha_Inicio],
    # Fecha_Fin = @[User::Fecha_Fin].
    df = df.copy()
    df["fecha_inicio"] = periodo.fecha_inicio
    df["fecha_fin"] = periodo.fecha_fin
    return df
