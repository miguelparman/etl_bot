"""Capa de infraestructura: autenticacion app-only y subida de archivos a
SharePoint via Microsoft Graph.

Mismo patron que 11_correos / 02_ventas: 'requests' + client credentials
(sin msal), subida simple <=4MB y por upload session (chunks de 5MB) >4MB,
reemplazando el archivo si ya existe.
"""

from __future__ import annotations

from urllib.parse import quote

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

_SIMPLE_UPLOAD_MAX_BYTES = 4 * 1024 * 1024
_CHUNK_SIZE_BYTES = 5 * 1024 * 1024  # multiplo de 320 KiB, tamano recomendado por Graph


class SharePointError(RuntimeError):
    """Fallo autenticando, resolviendo o subiendo contra Microsoft Graph."""


def get_graph_token(tenant_id: str, client_id: str, client_secret: str, timeout_ms: int) -> str:
    """Solicita un access token de aplicacion (scope .default) y lo devuelve."""
    try:
        response = requests.post(
            _TOKEN_URL_TEMPLATE.format(tenant_id=tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=timeout_ms / 1000,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        raise SharePointError(f"No se pudo obtener el token de Microsoft Graph (HTTP {status})") from None

    return response.json()["access_token"]


class SharePointClient:
    def __init__(self, token: str, timeout_ms: int) -> None:
        self._token = token
        self._timeout_s = timeout_ms / 1000

    def resolve_site(self, hostname: str, site_path: str) -> str:
        return self._get(f"{GRAPH_BASE}/sites/{hostname}:{site_path}")["id"]

    def resolve_drive(self, site_id: str, drive_name: str) -> str:
        """drive_name vacio = drive por defecto del site."""
        if not drive_name:
            return self._get(f"{GRAPH_BASE}/sites/{site_id}/drive")["id"]
        drives = self._get(f"{GRAPH_BASE}/sites/{site_id}/drives").get("value", [])
        for drive in drives:
            if drive.get("name", "").strip().lower() == drive_name.strip().lower():
                return drive["id"]
        disponibles = [d.get("name") for d in drives]
        raise SharePointError(f"No se encontro el drive '{drive_name}'. Drives disponibles: {disponibles}")

    def resolve_folder(self, drive_id: str, folder_path: str) -> str:
        return self._get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{quote(folder_path)}")["id"]

    def upload_file(self, drive_id: str, folder_id: str, filename: str, content: bytes) -> None:
        if len(content) <= _SIMPLE_UPLOAD_MAX_BYTES:
            url = f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}:/{quote(filename)}:/content"
            response = requests.put(url, headers=self._headers(), data=content, timeout=self._timeout_s)
            self._raise_for_upload_error(response, filename)
            return

        session_url = f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}:/{quote(filename)}:/createUploadSession"
        session_response = requests.post(
            session_url,
            headers=self._headers(),
            json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
            timeout=self._timeout_s,
        )
        self._raise_for_upload_error(session_response, filename)
        upload_url = session_response.json()["uploadUrl"]

        size = len(content)
        offset = 0
        while offset < size:
            chunk = content[offset : offset + _CHUNK_SIZE_BYTES]
            chunk_headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{offset + len(chunk) - 1}/{size}",
            }
            # La sesion de carga es publica (no lleva Authorization).
            chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk, timeout=self._timeout_s)
            self._raise_for_upload_error(chunk_response, filename)
            offset += len(chunk)

    def _raise_for_upload_error(self, response: requests.Response, filename: str) -> None:
        if not response.ok:
            raise SharePointError(
                f"Fallo al subir '{filename}' a SharePoint (HTTP {response.status_code}): {response.text[:300]}"
            )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self._headers(), timeout=self._timeout_s)
        if not response.ok:
            raise SharePointError(f"Error Graph {response.status_code} en {url}: {response.text[:500]}")
        return response.json()
