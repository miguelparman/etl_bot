"""Paso 0: copia 'FUNNEL VENTAS V2.xlsx' desde el sitio SharePoint 'BPO'
(Documentos compartidos/Planificación y Control/Insumos/Chile/Ventas_Chile)
hacia la carpeta '07 CROSS' de 'ReportingFractalia'.

'main.py' llama a 'copiar_funnel_ventas()' automaticamente antes de correr
el paquete 'ventas' (o 'todos'), asi siempre procesa la version mas
reciente del Excel sin depender de que alguien se acuerde de correrlo a
mano. Se deja como script standalone (ver 'Uso' abajo) solo para poder
refrescar el Excel sin correr el resto del pipeline.

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

from config import SharePointOrigenSettings, cargar_configuracion, cargar_configuracion_origen
from exceptions import ExtraccionError, VentasError
from logging_setup import CONSOLA, NOMBRE_LOGGER, configurar_logging
from mappings import ARCHIVO_FUNNEL_VENTAS_XLSX
from sharepoint.auth import get_graph_token
from sharepoint.client import SharePointClient

logger = logging.getLogger(NOMBRE_LOGGER)


def copiar_funnel_ventas(
    origen: SharePointOrigenSettings, cliente_destino: SharePointClient, drive_id_destino: str, folder_path_destino: str
) -> int:
    """Descarga 'FUNNEL VENTAS V2.xlsx' del tenant 'BPO' (autenticandose por
    su cuenta, ver SharePointOrigenSettings) y lo sube (reemplazando) a
    'folder_path_destino', reutilizando un SharePointClient ya autenticado
    contra el tenant destino (mismo que usan los Origen Excel/CSV de
    main.py). Devuelve los bytes subidos. Levanta ExtraccionError ante
    cualquier fallo de red/Graph -- lo que llama a esta funcion decide si
    aborta o no."""
    try:
        token_origen = get_graph_token(origen.tenant_id, origen.client_id, origen.client_secret, origen.timeout_ms)
        cliente_origen = SharePointClient(token_origen, origen.timeout_ms)
        site_id_origen = cliente_origen.resolve_site(origen.hostname, origen.site_path)
        drive_id_origen = cliente_origen.resolve_default_drive(site_id_origen)

        logger.info("Descargando '%s' (sitio '%s', tenant origen)...", origen.file_path, origen.site_path)
        contenido = cliente_origen.download_file(drive_id_origen, origen.file_path)

        folder_id_destino = cliente_destino.resolve_folder(drive_id_destino, folder_path_destino)

        logger.info(
            "Subiendo '%s' (%s bytes) hacia carpeta '%s'...",
            ARCHIVO_FUNNEL_VENTAS_XLSX,
            len(contenido),
            folder_path_destino,
        )
        cliente_destino.upload_file(drive_id_destino, folder_id_destino, ARCHIVO_FUNNEL_VENTAS_XLSX, contenido)
        return len(contenido)
    except Exception as exc:
        raise ExtraccionError(f"No se pudo copiar '{ARCHIVO_FUNNEL_VENTAS_XLSX}': {exc}") from exc


def main() -> int:
    settings = cargar_configuracion(BASE_DIR)
    origen = cargar_configuracion_origen(BASE_DIR)
    configurar_logging(settings.log_file)

    try:
        token_destino = get_graph_token(
            settings.sharepoint.tenant_id,
            settings.sharepoint.client_id,
            settings.sharepoint.client_secret,
            settings.sharepoint.timeout_ms,
        )
        cliente_destino = SharePointClient(token_destino, settings.sharepoint.timeout_ms)
        site_id_destino = cliente_destino.resolve_site(settings.sharepoint.hostname, settings.sharepoint.site_path)
        drive_id_destino = cliente_destino.resolve_drive(site_id_destino, settings.sharepoint.drive_name)

        bytes_copiados = copiar_funnel_ventas(origen, cliente_destino, drive_id_destino, settings.sharepoint.folder_path)

        logger.info("Copia completada (%s bytes).", bytes_copiados, extra=CONSOLA)
        return 0
    except VentasError as exc:
        logger.error("Error de configuracion: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo la copia de '%s': %s", ARCHIVO_FUNNEL_VENTAS_XLSX, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
