"""Implementacion concreta del puerto CsvDownloader.

Port directo de la dependencia externa invocada por el Execute Process Task
"Descargar googledrive señalizaciones" del paquete CROSS 0101
SSIS_CL_Senalizaciones.dtsx:

    python.exe "...\\02_Cross\\Ch_Senhalizaciones.py"

Logica original (Ch_Senhalizaciones.py): descarga el CSV publicado de una
hoja de Google Sheets, descarta las filas cuya primera columna esta vacia,
y escribe solo las primeras `num_columns` columnas en el destino, todo el
texto entre comillas.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class GoogleSheetsCsvDownloader:
    def __init__(self, export_url: str, destination_path: Path, num_columns: int = 39) -> None:
        self._export_url = export_url
        self._destination_path = destination_path
        self._num_columns = num_columns

    def download(self) -> Path:
        logger.info("Descargando CSV de Señalizaciones desde Google Sheets")
        response = requests.get(self._export_url, timeout=60)
        response.raise_for_status()

        lines = response.content.decode("utf-8").splitlines()
        reader = csv.reader(lines)

        self._destination_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._destination_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            for row in reader:
                if not row or not row[0]:
                    continue
                writer.writerow(row[: self._num_columns])

        logger.info("CSV de Señalizaciones escrito en %s", self._destination_path)
        return self._destination_path
