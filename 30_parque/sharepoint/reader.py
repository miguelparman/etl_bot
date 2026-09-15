"""Lector de CSV publicados en SharePoint via Microsoft Graph.

Reemplaza al Origen OLE DB (Connection Manager 'srv_chile' -> Externos_Frac)
del .dtsx original: en vez de una consulta SQL contra
Externos_Frac.dbo.pqe_fijtot2023 / pqe_movtot2023, el origen es el mismo
archivo pero exportado como CSV a SharePoint (mismo nombre que la tabla).

'keep_default_na=False' + 'na_values=[""]' evita que pandas interprete
valores de texto legitimos (p.ej. un RUT o telefono que por coincidencia sea
'NA', 'NULL', 'None', etc.) como nulos -- todo el origen original es texto
plano (DT_STR), sin tipado real, asi que solo una celda vacia se trata como
nulo.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from exceptions import ExtraccionError
from sharepoint.client import SharePointClient


class SharePointCsvReader:
    def __init__(
        self,
        client: SharePointClient,
        drive_id: str,
        folder_path: str,
        delimiter: str = ",",
    ) -> None:
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
