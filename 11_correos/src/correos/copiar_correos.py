"""Copia todos los archivos Excel de 'Control Correos Chile' (sitio 'BPO')
hacia '14 CORREOS' (sitio 'ReportingFractalia', carpeta 'BPOCHIPE').

'BPO' y 'ReportingFractalia' son tenants de Microsoft Entra DISTINTOS, cada
uno con su propio App Registration/credenciales (ver config.py) -- por eso
no se puede usar el endpoint de copia asincrona nativo de Graph ('POST
.../copy'), que solo copia dentro del mismo tenant/token. En vez de eso, se
descarga cada archivo con el token de 'BPO' y se sube con el token de
'ReportingFractalia' (mismo patron que 02_ventas/copiar_funnel_ventas.py).

No recorre subcarpetas: 'Control Correos Chile' tiene una subcarpeta
'Macros_Coordinadores' con macros .bas de los coordinadores que no forma
parte de esta copia (confirmado con el usuario)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import SharePointOrigenSettings
from exceptions import CorreosError
from logging_setup import NOMBRE_LOGGER
from sharepoint_auth import get_graph_token
from sharepoint_client import SharePointClient

logger = logging.getLogger(NOMBRE_LOGGER)


@dataclass(frozen=True)
class ResultadoArchivo:
    nombre: str
    bytes_copiados: int | None  # None si fallo
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def copiar_correos(
    origen: SharePointOrigenSettings,
    cliente_destino: SharePointClient,
    drive_id_destino: str,
    folder_id_destino: str,
) -> list[ResultadoArchivo]:
    """Autentica contra el tenant origen ('BPO'), lista los .xlsx de su
    carpeta y copia uno por uno hacia la carpeta destino (ya resuelta, sobre
    un SharePointClient ya autenticado contra el tenant 'ReportingFractalia'
    -- ver main.py). Un archivo que falla no detiene el resto: se registra
    el error y se continua con el siguiente. Devuelve el resultado de cada
    archivo."""
    token_origen = get_graph_token(origen.tenant_id, origen.client_id, origen.client_secret, origen.timeout_ms)
    cliente_origen = SharePointClient(token_origen, origen.timeout_ms)
    site_id_origen = cliente_origen.resolve_site(origen.hostname, origen.site_path)
    drive_id_origen = cliente_origen.resolve_default_drive(site_id_origen)

    nombres = cliente_origen.list_excel_files(drive_id_origen, origen.folder_path)
    logger.info("%s archivo(s) Excel encontrados en '%s'.", len(nombres), origen.folder_path)

    resultados: list[ResultadoArchivo] = []
    for nombre in nombres:
        file_path = f"{origen.folder_path}/{nombre}"
        try:
            contenido = cliente_origen.download_file(drive_id_origen, file_path)
            cliente_destino.upload_file(drive_id_destino, folder_id_destino, nombre, contenido)
            logger.info("Copiado '%s' (%s bytes).", nombre, len(contenido))
            resultados.append(ResultadoArchivo(nombre=nombre, bytes_copiados=len(contenido)))
        except CorreosError as exc:
            logger.error("Fallo copiando '%s': %s", nombre, exc)
            resultados.append(ResultadoArchivo(nombre=nombre, bytes_copiados=None, error=str(exc)))

    return resultados
