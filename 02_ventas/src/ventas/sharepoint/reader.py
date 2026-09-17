"""Lectores de archivos publicados en SharePoint via Microsoft Graph.

Reemplazan, como ORIGEN, a los Connection Manager OLE DB/EXCEL/FLATFILE de
los .dtsx originales: en vez de un archivo de red local o una descarga
puntual de Google Drive, el origen es el mismo archivo publicado en la
carpeta '07 CROSS' de SharePoint (ver README, seccion "Alcance de origenes").

- 'Señalizaciones.csv' (Flat File original) -> SharePointCsvReader.
- 'Base Carta Meta.xlsx' / 'FUNNEL VENTAS V2.xlsx' (Excel originales, cada
  uno con varias hojas) -> SharePointExcelReader, una hoja a la vez (misma
  granularidad que un 'Origen de Excel' del .dtsx, que siempre apuntaba a
  UNA hoja).
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from exceptions import ExtraccionError
from sharepoint.client import SharePointClient


class SharePointCsvReader:
    """'keep_default_na=False' + 'na_values=[""]' evita que pandas interprete
    valores de texto legitimos (p.ej. un comentario que por coincidencia sea
    'NA', 'NULL', 'None', etc.) como nulos -- el Flat File original es texto
    plano (DT_STR) sin tipado real, asi que solo una celda vacia se trata
    como nulo."""

    def __init__(self, client: SharePointClient, drive_id: str, folder_path: str, delimiter: str = ",") -> None:
        self._client = client
        self._drive_id = drive_id
        self._folder_path = folder_path.strip("/")
        self._delimiter = delimiter

    def leer_csv(self, nombre_archivo: str) -> pd.DataFrame:
        ruta = f"{self._folder_path}/{nombre_archivo}"
        try:
            contenido = self._client.download_file(self._drive_id, ruta)
        except Exception as exc:
            raise ExtraccionError(f"No se pudo descargar '{ruta}' desde SharePoint: {exc}") from exc

        try:
            return pd.read_csv(
                BytesIO(contenido),
                dtype=str,
                sep=self._delimiter,
                keep_default_na=False,
                na_values=[""],
            )
        except Exception as exc:
            raise ExtraccionError(f"No se pudo parsear el CSV '{nombre_archivo}': {exc}") from exc


class SharePointExcelReader:
    """Lee una hoja puntual de un workbook Excel publicado en SharePoint.
    Equivalente a un Origen de Excel (Provider=Microsoft.ACE.OLEDB) apuntando
    a 'HOJA$' -- se descarga el workbook completo (Graph no permite leer una
    hoja parcialmente) y se parsea solo la hoja pedida con openpyxl."""

    def __init__(self, client: SharePointClient, drive_id: str, folder_path: str) -> None:
        self._client = client
        self._drive_id = drive_id
        self._folder_path = folder_path.strip("/")

    def leer_hoja(self, nombre_archivo: str, hoja: str) -> pd.DataFrame:
        ruta = f"{self._folder_path}/{nombre_archivo}"
        try:
            contenido = self._client.download_file(self._drive_id, ruta)
        except Exception as exc:
            raise ExtraccionError(f"No se pudo descargar '{ruta}' desde SharePoint: {exc}") from exc

        try:
            return pd.read_excel(BytesIO(contenido), sheet_name=hoja, engine="openpyxl")
        except Exception as exc:
            raise ExtraccionError(f"No se pudo parsear la hoja '{hoja}' de '{nombre_archivo}': {exc}") from exc
