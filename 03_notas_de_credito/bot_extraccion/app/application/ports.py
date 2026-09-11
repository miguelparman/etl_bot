"""
Puertos (interfaces) que la capa de aplicación necesita para orquestar el
caso de uso, sin conocer la tecnología concreta (Playwright, sistema de
archivos, ...) que los implementa. Las implementaciones reales viven en
app/infrastructure/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ReportExtractor(Protocol):
    """Etapa 'Extract': sabe autenticarse, navegar y exportar la tabla objetivo de un informe."""

    def extraer(self) -> Path:
        """Ejecuta el flujo de extracción y devuelve la ruta del archivo descargado."""
        ...


class ArchivoLoader(Protocol):
    """Etapa 'Load': sabe depositar un archivo extraído en su destino final."""

    def guardar(self, origen: Path, destino: Path) -> Path:
        """Copia 'origen' a 'destino' (sobrescribiendo si existe) y devuelve la ruta final."""
        ...
