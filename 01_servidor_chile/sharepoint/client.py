"""
SharePointClient: resolucion de Site, Drive y Folder via Microsoft Graph,
por ruta (hostname + site path, nombre de drive, ruta de carpeta).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import requests

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
        return data["id"]

    def resolve_drive(self, site_id: str, drive_name: str) -> str:
        data = self._get(f"{GRAPH_BASE}/sites/{site_id}/drives")
        drives = data.get("value", [])
        for drive in drives:
            if drive.get("name", "").strip().lower() == drive_name.strip().lower():
                return drive["id"]
        available = [d.get("name") for d in drives]
        raise SharePointResolutionError(
            f"No se encontro el drive '{drive_name}' en el site. Drives disponibles: {available}"
        )

    def resolve_folder(self, drive_id: str, folder_path: str) -> str:
        data = self._get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{quote(folder_path)}")
        return data["id"]

    def resolve_default_drive(self, site_id: str) -> str:
        """Devuelve el ID del drive por defecto del site (biblioteca de documentos principal)."""
        data = self._get(f"{GRAPH_BASE}/sites/{site_id}/drive")
        return data["id"]

    def list_folder(self, drive_id: str, folder_path: str) -> list:
        """Lista los items (archivos y subcarpetas) dentro de una carpeta."""
        data = self._get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{quote(folder_path)}:/children")
        return data.get("value", [])

    def resolve_target(
        self, hostname: str, site_path: str, drive_name: str, folder_path: str
    ) -> SharePointTarget:
        site_id = self.resolve_site(hostname, site_path)
        drive_id = self.resolve_drive(site_id, drive_name)
        folder_id = self.resolve_folder(drive_id, folder_path)
        return SharePointTarget(site_id=site_id, drive_id=drive_id, folder_id=folder_id)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self._headers(), timeout=self._timeout_s)
        if response.status_code == 404:
            raise SharePointResolutionError(f"Recurso no encontrado en Graph: {url}")
        if not response.ok:
            raise SharePointResolutionError(
                f"Error Graph {response.status_code} en {url}: {response.text[:500]}"
            )
        return response.json()
