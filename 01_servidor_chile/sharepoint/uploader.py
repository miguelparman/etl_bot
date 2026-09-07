"""
Carga de archivos a SharePoint via Microsoft Graph.

- Archivos <= 4 MB: PUT .../content (subida simple, sobreescribe si ya existe).
- Archivos > 4 MB: createUploadSession con chunks de 5 MB (conflictBehavior=replace).
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import requests

from .client import GRAPH_BASE

_SIMPLE_UPLOAD_MAX_BYTES = 4 * 1024 * 1024
_CHUNK_SIZE_BYTES = 5 * 1024 * 1024  # multiplo de 320 KiB, tamano recomendado por Graph


class SharePointUploadError(Exception):
    """Fallo subiendo un archivo a SharePoint."""


class SharePointUploader:
    def __init__(self, token: str, drive_id: str, folder_id: str, timeout_ms: int) -> None:
        self._token = token
        self._drive_id = drive_id
        self._folder_id = folder_id
        self._timeout_s = timeout_ms / 1000

    def upload(self, local_path: Path) -> None:
        size = local_path.stat().st_size
        if size <= _SIMPLE_UPLOAD_MAX_BYTES:
            self._upload_simple(local_path)
        else:
            self._upload_in_chunks(local_path, size)

    def _upload_simple(self, local_path: Path) -> None:
        url = f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._folder_id}:/{quote(local_path.name)}:/content"
        with local_path.open("rb") as fh:
            response = requests.put(url, headers=self._headers(), data=fh, timeout=self._timeout_s)
        self._raise_for_upload_error(response, local_path.name)

    def _upload_in_chunks(self, local_path: Path, size: int) -> None:
        session_url = (
            f"{GRAPH_BASE}/drives/{self._drive_id}/items/{self._folder_id}:/"
            f"{quote(local_path.name)}:/createUploadSession"
        )
        session_response = requests.post(
            session_url,
            headers=self._headers(),
            json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
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

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _raise_for_upload_error(self, response: requests.Response, filename: str) -> None:
        if response.ok:
            return
        raise SharePointUploadError(
            f"Fallo al subir '{filename}' a SharePoint (HTTP {response.status_code}): {response.text[:300]}"
        )
