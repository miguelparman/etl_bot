"""Puerto (interfaz) para leer hojas de Excel.

Equivalente al componente Excel Source (Microsoft.ExcelSource, AccessMode=0)
usado en todos los Data Flow Tasks que leen desde archivos .xlsx.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class SpreadsheetReader(Protocol):
    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        """Lee una hoja completa de un libro Excel como DataFrame."""
        ...
