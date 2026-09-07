"""
Lista el contenido de una carpeta del site BPO en SharePoint via Microsoft
Graph, usando el mismo tenant/app registrados en .env de este proyecto.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sharepoint.auth import get_graph_token
from sharepoint.client import SharePointClient

load_dotenv()

TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
GRAPH_TIMEOUT_MS = int(os.environ.get("GRAPH_TIMEOUT", "120000"))

SHAREPOINT_HOSTNAME = os.environ.get("SHAREPOINT_HOSTNAME", "fractaliagroup.sharepoint.com")
SITE_PATH = "/sites/BPO"
FOLDER_PATH = "Planificación y Control/Insumos/Horarios/202601"


def main():
    token = get_graph_token(TENANT_ID, CLIENT_ID, CLIENT_SECRET, GRAPH_TIMEOUT_MS)
    client = SharePointClient(token, GRAPH_TIMEOUT_MS)

    site_id = client.resolve_site(SHAREPOINT_HOSTNAME, SITE_PATH)
    drive_id = client.resolve_default_drive(site_id)
    items = client.list_folder(drive_id, FOLDER_PATH)

    print(f"{len(items)} elemento(s) en '{FOLDER_PATH}':\n")
    for item in sorted(items, key=lambda i: i["name"].lower()):
        tipo = "carpeta" if "folder" in item else "archivo"
        tam = item.get("size", 0)
        print(f"  [{tipo:7}] {item['name']:60} {tam:>10} bytes")


if __name__ == "__main__":
    main()
