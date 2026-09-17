"""Lectura del Excel de origen con pandas/openpyxl. Equivalente al Connection
Manager Excel 'CARTERA' del paquete original.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class SpreadsheetReader:
    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        """Devuelve la hoja completa, sin tipar ni sanear (eso lo hace
        extraction.py)."""
        return pd.read_excel(path, sheet_name=sheet_name, dtype=str)
