"""Paso 0 (previo al pipeline, se corre a mano cuando el usuario actualiza el
Excel de origen): copia 'FUNNEL VENTAS V2.xlsx' desde el sitio SharePoint
'BPO' (Documentos compartidos/Planificación y Control/Insumos/Chile/
Ventas_Chile) hacia la carpeta '07 CROSS' de 'ReportingFractalia'.

'BPO' y 'ReportingFractalia' son tenants de Microsoft Entra DISTINTOS, cada
uno con su propio App Registration/credenciales (ver config.py,
SharePointOrigenSettings vs SharePointSettings, y .env.example) -- por eso
no se puede usar el endpoint de copia asincrona nativo de Graph (que solo
copia dentro del mismo tenant/token que hizo la llamada): se descarga el
archivo con el token de 'BPO' y se sube con el token de 'ReportingFractalia'
(ver sharepoint/client.py, SharePointClient.download_file/upload_file).

Uso:
    python copiar_funnel_ventas.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src" / "ventas"))

from config import cargar_configuracion, cargar_configuracion_origen
from exceptions import VentasError
from logging_setup import NOMBRE_LOGGER, configurar_logging
from mappings import ARCHIVO_FUNNEL_VENTAS_XLSX
from sharepoint.auth import get_graph_token
from sharepoint.client import SharePointClient

logger = logging.getLogger(NOMBRE_LOGGER)


def main() -> int:
    settings = cargar_configuracion(BASE_DIR)
    origen = cargar_configuracion_origen(BASE_DIR)
    configurar_logging(settings.log_file)

    try:
        token_origen = get_graph_token(origen.tenant_id, origen.client_id, origen.client_secret, origen.timeout_ms)
        cliente_origen = SharePointClient(token_origen, origen.timeout_ms)
        site_id_origen = cliente_origen.resolve_site(origen.hostname, origen.site_path)
        drive_id_origen = cliente_origen.resolve_default_drive(site_id_origen)

        logger.info("Descargando '%s' (sitio '%s', tenant origen)...", origen.file_path, origen.site_path)
        contenido = cliente_origen.download_file(drive_id_origen, origen.file_path)

        token_destino = get_graph_token(
            settings.sharepoint.tenant_id,
            settings.sharepoint.client_id,
            settings.sharepoint.client_secret,
            settings.sharepoint.timeout_ms,
        )
        cliente_destino = SharePointClient(token_destino, settings.sharepoint.timeout_ms)
        site_id_destino = cliente_destino.resolve_site(settings.sharepoint.hostname, settings.sharepoint.site_path)
        drive_id_destino = cliente_destino.resolve_drive(site_id_destino, settings.sharepoint.drive_name)
        folder_id_destino = cliente_destino.resolve_folder(drive_id_destino, settings.sharepoint.folder_path)

        logger.info(
            "Subiendo '%s' hacia sitio '%s', carpeta '%s'...",
            ARCHIVO_FUNNEL_VENTAS_XLSX,
            settings.sharepoint.site_path,
            settings.sharepoint.folder_path,
        )
        cliente_destino.upload_file(drive_id_destino, folder_id_destino, ARCHIVO_FUNNEL_VENTAS_XLSX, contenido)

        logger.info("Copia completada (%s bytes).", len(contenido))
        return 0
    except VentasError as exc:
        logger.error("Error de configuracion: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo la copia de '%s': %s", ARCHIVO_FUNNEL_VENTAS_XLSX, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
