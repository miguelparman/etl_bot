"""Lectura del Excel de origen desde SharePoint (Microsoft Graph) con
pandas/openpyxl. Equivalente al Connection Manager Excel 'CARTERA' del paquete
original, que apuntaba a una ruta local/de red; ahora el mismo archivo
(CARTERA_FRACTALIA.xlsx) se descarga del sitio ReportingFractalia.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from sharepoint.client import SharePointClient


class SpreadsheetReader:
    def __init__(self, client: SharePointClient, drive_id: str) -> None:
        self._client = client
        self._drive_id = drive_id

    def read_sheet(self, path: str, sheet_name: str) -> pd.DataFrame:
        """Descarga 'path' (ruta del archivo dentro del drive: carpeta +
        nombre) y devuelve la hoja completa, sin tipar ni sanear (eso lo hace
        extraccion/extractor.py)."""
        contenido = self._client.download_file(self._drive_id, path.strip("/"))
        return pd.read_excel(BytesIO(contenido), sheet_name=sheet_name, dtype=str)
