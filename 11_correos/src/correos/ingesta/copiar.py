"""INGESTA: copia todos los archivos Excel de 'Control Correos Chile' (sitio
'BPO') hacia '14 CORREOS' (sitio 'ReportingFractalia', carpeta 'BPOCHIPE'),
de donde los lee bronze.

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

from comun.config import Settings, SharePointOrigenSettings
from comun.exceptions import CorreosError
from comun.logging_setup import NOMBRE_LOGGER
from comun.sharepoint_auth import get_graph_token
from comun.sharepoint_client import SharePointClient, conectar_destino

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
    -- ver ejecutar_copia()). Un archivo que falla no detiene el resto: se registra
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


def ejecutar_copia(settings: Settings) -> list[ResultadoArchivo]:
    """Resuelve la carpeta destino y copia. Registra el resumen en el log.
    Levanta CorreosError si no se pudo resolver el origen o el destino (un
    archivo individual que falla no levanta: queda en el resultado)."""
    cliente_destino, drive_id_destino = conectar_destino(settings.destino)
    folder_id_destino = cliente_destino.resolve_folder(drive_id_destino, settings.destino.folder_path)

    resultados = copiar_correos(settings.origen, cliente_destino, drive_id_destino, folder_id_destino)

    fallidos = [r for r in resultados if not r.ok]
    logger.info(
        "Copia finalizada: %s exitoso(s), %s fallido(s) de %s archivo(s).",
        len(resultados) - len(fallidos),
        len(fallidos),
        len(resultados),
    )
    for r in fallidos:
        logger.error("  - %s: %s", r.nombre, r.error)
    return resultados
