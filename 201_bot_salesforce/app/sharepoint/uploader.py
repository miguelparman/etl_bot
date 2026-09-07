"""
Carga de archivos a SharePoint via Microsoft Graph.

- Archivos <= 4 MB: PUT .../content (subida simple).
- Archivos > 4 MB: createUploadSession con chunks de 5 MB.
- Respeta OVERWRITE_EXISTING: si es false y el archivo ya existe, se omite
  la subida en vez de fallar (ver Fase 1, seccion 17).

Los reintentos con backoff y el respeto de Retry-After ante 429 se
incorporan en la Fase 9, junto con el resto del manejo de errores
centralizado.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import requests

from app.logger import log
from app.sharepoint.client import GRAPH_BASE

_SIMPLE_UPLOAD_MAX_BYTES = 4 * 1024 * 1024
_CHUNK_SIZE_BYTES = 5 * 1024 * 1024  # multiplo de 320 KiB, tamano recomendado por Graph


class SharePointUploadError(Exception):
    """Fallo subiendo un archivo a SharePoint."""


class SharePointUploader:
    def __init__(self, token: str, drive_id: str, default_folder_id: str, timeout_ms: int, overwrite: bool) -> None:
        self._token = token
        self._drive_id = drive_id
        self._default_folder_id = default_folder_id
        self._timeout_s = timeout_ms / 1000
        self._overwrite = overwrite

    def upload(self, local_path: Path, folder_id: str | None = None) -> bool:
        """Sube local_path a la carpeta destino, eligiendo PUT simple o
        sesion de carga por chunks segun el tamano del archivo.

        `folder_id` permite que un informe puntual use una subcarpeta
        distinta a la carpeta por defecto (mismo drive siempre). Si se
        omite, se usa la carpeta por defecto resuelta al iniciar.

        Devuelve True si se subio el archivo, False si se omitio porque ya
        existia y OVERWRITE_EXISTING=false.
        """
        filename = local_path.name
        target_folder_id = folder_id or self._default_folder_id

        if not self._overwrite and self._target_exists(filename, target_folder_id):
            log.warning(
                "El archivo '%s' ya existe en SharePoint y OVERWRITE_EXISTING=false; se omite la subida.",
                filename,
            )
            return False

        size = local_path.stat().st_size
        if size <= _SIMPLE_UPLOAD_MAX_BYTES:
            self._upload_simple(local_path, target_folder_id)
        else:
            self._upload_in_chunks(local_path, size, target_folder_id)

        log.info("Archivo cargado correctamente en SharePoint: %s", filename)
        return True

    # -- Estrategias de subida -----------------------------------------------

    def _upload_simple(self, local_path: Path, folder_id: str) -> None:
        url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{folder_id}:/{quote(local_path.name)}:/content"
        with local_path.open("rb") as fh:
            response = requests.put(url, headers=self._headers(), data=fh, timeout=self._timeout_s)
        self._raise_for_upload_error(response, local_path.name)

    def _upload_in_chunks(self, local_path: Path, size: int, folder_id: str) -> None:
        conflict_behavior = "replace" if self._overwrite else "fail"
        session_url = (
            f"{GRAPH_BASE}/drives/{self._drive_id}/items/{folder_id}:/"
            f"{quote(local_path.name)}:/createUploadSession"
        )
        session_response = requests.post(
            session_url,
            headers=self._headers(),
            json={"item": {"@microsoft.graph.conflictBehavior": conflict_behavior}},
            timeout=self._timeout_s,
        )
        self._raise_for_upload_error(session_response, local_path.name)
        upload_url = session_response.json()["uploadUrl"]

        with local_path.open("rb") as fh:
            offset = 0
            while offset < size:
                chunk = fh.read(_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                chunk_headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{offset + len(chunk) - 1}/{size}",
                }
                # La sesion de carga es publica (no lleva Authorization).
                chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk, timeout=self._timeout_s)
                self._raise_for_upload_error(chunk_response, local_path.name)
                offset += len(chunk)

    # -- Helpers ---------------------------------------------------------

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _target_exists(self, filename: str, folder_id: str) -> bool:
        url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{folder_id}:/{quote(filename)}"
        response = requests.get(url, headers=self._headers(), timeout=self._timeout_s)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def _raise_for_upload_error(self, response: requests.Response, filename: str) -> None:
        if response.ok:
            return
        error = SharePointUploadError(
            f"Fallo al subir '{filename}' a SharePoint (HTTP {response.status_code}): {response.text[:300]}"
        )
        # Se adjunta la respuesta para que app.services.retry pueda respetar
        # la cabecera Retry-After si Graph responde 429 (throttling).
        error.response = response
        raise error
