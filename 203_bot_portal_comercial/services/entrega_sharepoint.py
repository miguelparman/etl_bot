"""Entrega comun de los archivos descargados: subida via Microsoft Graph a
cada destino SharePoint configurado (settings.destinos_sharepoint).

Si un destino falla se intentan igual los demas; al final se lanza un error
con el detalle de los que fallaron.
"""

import logging

from config.settings import SharePointDestino
from core.sharepoint_client import SharePointClient, get_graph_token


def subir_a_sharepoint(
    destinos: tuple[SharePointDestino, ...],
    nombre_archivo: str,
    contenido: bytes,
    timeout_ms: int,
    log: logging.Logger,
) -> None:
    errores = []
    for destino in destinos:
        try:
            token = get_graph_token(destino.tenant_id, destino.client_id, destino.client_secret, timeout_ms)
            client = SharePointClient(token, timeout_ms)

            site_id = client.resolve_site(destino.hostname, destino.site_path)
            drive_id = client.resolve_drive(site_id, destino.drive_name)
            folder_id = client.resolve_folder(drive_id, destino.folder_path)
            client.upload_file(drive_id, folder_id, nombre_archivo, contenido)

            log.info("Subido a SharePoint '%s': %s/%s", destino.nombre, destino.folder_path, nombre_archivo)
        except Exception as e:
            log.exception("Error subiendo %s a SharePoint '%s'", nombre_archivo, destino.nombre)
            errores.append(f"{destino.nombre}: {e}")

    if errores:
        raise RuntimeError(f"Fallo la subida de {nombre_archivo} -> " + " | ".join(errores))
