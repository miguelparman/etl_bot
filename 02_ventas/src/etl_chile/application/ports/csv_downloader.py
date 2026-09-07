"""Puerto (interfaz) para obtener el CSV de Señalizaciones.

Equivalente al Execute Process Task "Descargar googledrive señalizaciones"
que invocaba `python.exe Ch_Senhalizaciones.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CsvDownloader(Protocol):
    def download(self) -> Path:
        """Descarga/genera el CSV de origen y devuelve la ruta final."""
        ...
