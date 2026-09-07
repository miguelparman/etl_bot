"""Extraccion: Data Flow 'CL_TEMPORALES TBL_CARTERA' de CL_Proc_Carga_Cartera.dtsx,
componentes 'Origen de Excel' + 'Conversion de datos' + 'Columna derivada'
(el cuarto componente, el Destino OLE DB, es responsabilidad de load.py).

No conoce pyodbc ni pandas.read_excel concreto -- solo el puerto
SpreadsheetReader (application/ports.py) y las reglas de saneo/tipado, que
son logica de negocio (los anchos de truncamiento y las columnas
descartadas son parte del proceso original, no un detalle tecnico de
lectura de archivos).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.application import mappings
from app.application.ports import SpreadsheetReader
from app.domain.exceptions import ExtraccionError
from app.domain.models import Periodo

logger = logging.getLogger("cartera")


class CarteraExcelExtractor:
    """Implementa la extraccion de la cartera desde el Excel de origen."""

    def __init__(self, spreadsheet_reader: SpreadsheetReader, excel_path: Path) -> None:
        self._spreadsheet_reader = spreadsheet_reader
        self._excel_path = excel_path

    def extraer(self, periodo: Periodo) -> pd.DataFrame:
        df = self._leer()
        df = self._truncar(df)
        df = self._agregar_periodo(df, periodo)
        return df[list(mappings.STAGING_INSERT_COLUMNS)]

    def _leer(self) -> pd.DataFrame:
        try:
            df = self._spreadsheet_reader.read_sheet(self._excel_path, mappings.EXCEL_SHEET)
        except Exception as exc:
            raise ExtraccionError(
                f"No se pudo leer el Excel '{self._excel_path}' (hoja '{mappings.EXCEL_SHEET}'): {exc}"
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

    def _truncar(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            for columna, largo in mappings.TRUNCATION_LENGTHS.items():
                df[columna] = df[columna].astype("string").str.slice(0, largo)
            return df
        except Exception as exc:
            raise ExtraccionError(f"No se pudieron tipar/truncar las columnas: {exc}") from exc

    def _agregar_periodo(self, df: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
        # Componente 'Columna derivada': Fecha_Inicio = @[User::Fecha_Inicio],
        # Fecha_Fin = @[User::Fecha_Fin].
        df = df.copy()
        df["fecha_inicio"] = periodo.fecha_inicio
        df["fecha_fin"] = periodo.fecha_fin
        return df
