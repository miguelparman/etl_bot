"""Adaptador de infraestructura: lectura de archivos Excel con pandas/openpyxl.

Implementa el puerto SpreadsheetReader (app/application/ports.py). Equivalente
al Connection Manager Excel 'CARTERA' del paquete original.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class PandasExcelReader:
    """Implementa el puerto SpreadsheetReader (app/application/ports.py)."""

    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        return pd.read_excel(path, sheet_name=sheet_name, dtype=str)
