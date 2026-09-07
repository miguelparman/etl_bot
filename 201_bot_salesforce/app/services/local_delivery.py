"""
Copia local/de red adicional de cada informe descargado, sumada a la
subida a SharePoint (no en su lugar). Pensada para una carpeta compartida
como 'D:\\IRISCENE ENGINEERING CORPORATION SLU\\BPO - Insumos\\Chile\\SEGUIMIENTO'.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.logger import log


class LocalDeliveryError(Exception):
    """Fallo copiando un informe a la carpeta local/red adicional."""


class LocalDeliveryCopier:
    def __init__(self, destination_dir: Path, overwrite: bool) -> None:
        self._default_destination_dir = destination_dir
        self._overwrite = overwrite

    def copy(self, local_path: Path, destination_dir: Path | None = None) -> bool:
        """Copia local_path a la carpeta destino.

        `destination_dir` permite que un informe puntual use una carpeta
        distinta a la carpeta por defecto. Si se omite, se usa la carpeta
        por defecto (LOCAL_COPY_DIR).

        Devuelve True si se copio, False si se omitio porque el archivo ya
        existia alli y OVERWRITE_EXISTING=false.
        """
        target_dir = destination_dir or self._default_destination_dir

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LocalDeliveryError(f"No se pudo acceder/crear la carpeta destino '{target_dir}': {exc}") from exc

        target = target_dir / local_path.name
        if target.exists() and not self._overwrite:
            log.warning(
                "El archivo '%s' ya existe en '%s' y OVERWRITE_EXISTING=false; se omite la copia.",
                local_path.name,
                target_dir,
            )
            return False

        try:
            shutil.copy2(local_path, target)
        except OSError as exc:
            raise LocalDeliveryError(f"No se pudo copiar '{local_path.name}' a '{target_dir}': {exc}") from exc

        log.info("Archivo copiado a la carpeta local adicional: %s", target)
        return True
