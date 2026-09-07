"""
SharePointClient: resolucion de Site, Drive y Folder via Microsoft Graph.

Estrategia (ver Fase 1, punto 9): resolver por ruta (hostname + site path,
nombre de drive, ruta de carpeta) y cachear los IDs resultantes. Si un ID
cacheado deja de ser valido (404), se re-resuelve automaticamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import requests

from app.logger import log

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class SharePointResolutionError(Exception):
    """No se pudo resolver el site, drive o carpeta destino en SharePoint."""


@dataclass
class SharePointTarget:
    site_id: str
    drive_id: str
    folder_id: str


class SharePointClient:
    def __init__(self, token: str, timeout_ms: int) -> None:
        self._token = token
        self._timeout_s = timeout_ms / 1000

    def resolve_site(self, hostname: str, site_path: str) -> str:
        data = self._get(f"{GRAPH_BASE}/sites/{hostname}:{site_path}")
        site_id = data["id"]
        log.info("Site de SharePoint resuelto: %s", site_id)
        return site_id

    def resolve_drive(self, site_id: str, drive_name: str) -> str:
        data = self._get(f"{GRAPH_BASE}/sites/{site_id}/drives")
        drives = data.get("value", [])
        for drive in drives:
            if drive.get("name", "").strip().lower() == drive_name.strip().lower():
                log.info("Drive de SharePoint resuelto: %s (%s)", drive["id"], drive_name)
                return drive["id"]
        available = [d.get("name") for d in drives]
        raise SharePointResolutionError(
            f"No se encontro el drive '{drive_name}' en el site. Drives disponibles: {available}"
        )

    def resolve_folder(self, drive_id: str, folder_path: str) -> str:
        data = self._get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{quote(folder_path)}")
        folder_id = data["id"]
        log.info("Carpeta de SharePoint resuelta: %s", folder_id)
        return folder_id

    def resolve_target(
        self,
        hostname: str,
        site_path: str,
        drive_name: str,
        folder_path: str,
        cached_site_id: str = "",
        cached_drive_id: str = "",
        cached_folder_id: str = "",
    ) -> SharePointTarget:
        """Usa los IDs cacheados si estan presentes y siguen siendo validos;
        si alguno ya no existe (404), re-resuelve solo lo necesario."""
        site_id = cached_site_id
        if site_id and self._get_optional(f"{GRAPH_BASE}/sites/{site_id}") is None:
            log.warning("El SHAREPOINT_SITE_ID cacheado ya no es valido, se vuelve a resolver.")
            site_id = ""
        if not site_id:
            site_id = self.resolve_site(hostname, site_path)

        drive_id = cached_drive_id
        if drive_id and self._get_optional(f"{GRAPH_BASE}/drives/{drive_id}") is None:
            log.warning("El SHAREPOINT_DRIVE_ID cacheado ya no es valido, se vuelve a resolver.")
            drive_id = ""
        if not drive_id:
            drive_id = self.resolve_drive(site_id, drive_name)

        folder_id = cached_folder_id
        if folder_id and self._get_optional(f"{GRAPH_BASE}/drives/{drive_id}/items/{folder_id}") is None:
            log.warning("El SHAREPOINT_FOLDER_ID cacheado ya no es valido, se vuelve a resolver.")
            folder_id = ""
        if not folder_id:
            folder_id = self.resolve_folder(drive_id, folder_path)

        return SharePointTarget(site_id=site_id, drive_id=drive_id, folder_id=folder_id)

    # -- Helpers HTTP -------------------------------------------------------

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self._headers(), timeout=self._timeout_s)
        if response.status_code == 404:
            raise SharePointResolutionError(f"Recurso no encontrado en Graph: {url}")
        response.raise_for_status()
        return response.json()

    def _get_optional(self, url: str) -> dict | None:
        """Como _get, pero devuelve None en vez de lanzar si el recurso no existe (404)."""
        response = requests.get(url, headers=self._headers(), timeout=self._timeout_s)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


class SharePointFolderResolver:
    """Resuelve la carpeta destino de un informe, permitiendo que cada uno
    use una subcarpeta distinta dentro del mismo site/drive (que siempre es
    el mismo). Si el informe no especifica una ruta propia, se usa la
    carpeta por defecto ya resuelta en main.py. Cachea cada ruta resuelta
    para no repetir la llamada a Graph si varios informes comparten la
    misma subcarpeta alternativa.
    """

    def __init__(self, client: SharePointClient, drive_id: str, default_folder_id: str) -> None:
        self._client = client
        self._drive_id = drive_id
        self._default_folder_id = default_folder_id
        self._cache: dict[str, str] = {}

    def resolve(self, folder_path: str | None) -> str:
        if not folder_path:
            return self._default_folder_id
        if folder_path not in self._cache:
            self._cache[folder_path] = self._client.resolve_folder(self._drive_id, folder_path)
        return self._cache[folder_path]
