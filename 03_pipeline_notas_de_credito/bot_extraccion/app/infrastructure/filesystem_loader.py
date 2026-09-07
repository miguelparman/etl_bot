"""Adaptador de infraestructura: implementa el puerto ArchivoLoader usando el sistema de archivos local."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.domain.exceptions import GuardadoError
from app.infrastructure.logging_setup import NOMBRE_LOGGER

logger = logging.getLogger(NOMBRE_LOGGER)


class FilesystemArchivoLoader:
    """Etapa 'Load': deposita el archivo extraído en su destino final, sobrescribiendo si existe."""

    def guardar(self, origen: Path, destino: Path) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            if destino.exists():
                destino.unlink()
            shutil.copy2(origen, destino)
        except PermissionError as exc:
            raise GuardadoError(
                f"No se pudo sobrescribir '{destino}'. Verifica que el archivo "
                "no esté abierto en Excel u otro programa."
            ) from exc
        logger.info(f"Archivo guardado en: {destino}")
        return destino
