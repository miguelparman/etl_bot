"""Capa BRONZE: consolida 'Registro'/'Bandejas' de todos los .xlsx en
'14 CORREOS' (sitio SharePoint 'ReportingFractalia', ya copiados por
ingesta) y los carga tal cual en SQL Server ('CL_MOVIL', 172.17.0.162):

- TBL_CORREO_REGISTRO: carga por PERIODO -- elimina solo las filas cuyo
  'FechaHora_UTC_Texto' cae en [inicio, fin) y vuelve a insertar unicamente
  los registros consolidados de ese mismo periodo. No afecta filas de otros
  periodos ya cargados.
- TBL_CORREO_BANDEJAS: siempre reemplazo COMPLETO (TRUNCATE + INSERT de
  todo lo consolidado), sin filtro de fecha -- no tiene un campo de control
  de periodo (ver README).

El periodo lo resuelve main.py (ver comun/periodo.py).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from bronze.consolidar import consolidar, preparar_bandejas, preparar_registro
from bronze.mappings import COLUMNA_CONTROL_FECHA, ESQUEMA, TABLA_BANDEJAS, TABLA_REGISTRO
from comun.config import SharePointDestinoSettings
from comun.db import DatabaseGateway
from comun.exceptions import CorreosError
from comun.logging_setup import NOMBRE_LOGGER
from comun.sharepoint_client import conectar_destino

logger = logging.getLogger(NOMBRE_LOGGER)


def descargar_archivos(destino: SharePointDestinoSettings) -> dict[str, bytes]:
    """Descarga todos los .xlsx de '14 CORREOS'. Un archivo que no se puede
    descargar se omite (se registra el motivo), no detiene al resto."""
    cliente, drive_id = conectar_destino(destino)
    nombres = cliente.list_excel_files(drive_id, destino.folder_path)
    logger.info("%s archivo(s) Excel encontrados en '%s'.", len(nombres), destino.folder_path)

    archivos: dict[str, bytes] = {}
    for nombre in nombres:
        try:
            archivos[nombre] = cliente.download_file(drive_id, f"{destino.folder_path}/{nombre}")
        except CorreosError as exc:
            logger.error("No se pudo descargar '%s', se omite: %s", nombre, exc)
    return archivos


def cargar(
    gateway: DatabaseGateway,
    registro_df: pd.DataFrame,
    bandejas_df: pd.DataFrame,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> tuple[int, int, int]:
    """Ejecuta la carga en SQL Server. 'registro_df' ya debe venir con
    'FechaHora_UTC_Texto'/'FechaHora' convertidos a datetime (ver
    consolidar.preparar_registro) y SIN filtrar por periodo -- el filtro se
    aplica aqui, para que el DELETE y el INSERT usen exactamente el mismo
    rango. Devuelve (filas_eliminadas, filas_insertadas_registro,
    filas_insertadas_bandejas)."""
    en_rango = (registro_df[COLUMNA_CONTROL_FECHA] >= fecha_inicio) & (registro_df[COLUMNA_CONTROL_FECHA] < fecha_fin)
    registro_periodo = registro_df[en_rango]
    logger.info(
        "%s de %s fila(s) de 'Registro' caen en el periodo [%s, %s).",
        len(registro_periodo),
        len(registro_df),
        fecha_inicio,
        fecha_fin,
    )

    filas_eliminadas = gateway.execute_script_rowcount(
        f"DELETE FROM [{ESQUEMA}].[{TABLA_REGISTRO}] WHERE [{COLUMNA_CONTROL_FECHA}] >= ? AND [{COLUMNA_CONTROL_FECHA}] < ?",
        (fecha_inicio, fecha_fin),
    )
    logger.info("%s fila(s) eliminadas de [%s].[%s] para el periodo.", filas_eliminadas, ESQUEMA, TABLA_REGISTRO)

    filas_insertadas_registro = gateway.bulk_insert(TABLA_REGISTRO, registro_periodo, schema=ESQUEMA)

    gateway.truncate_table(TABLA_BANDEJAS, schema=ESQUEMA)
    filas_insertadas_bandejas = gateway.bulk_insert(TABLA_BANDEJAS, bandejas_df, schema=ESQUEMA)

    return filas_eliminadas, filas_insertadas_registro, filas_insertadas_bandejas


def ejecutar_bronze(
    destino: SharePointDestinoSettings, gateway: DatabaseGateway, fecha_inicio: datetime, fecha_fin: datetime
) -> tuple[int, int, int]:
    """Descarga los .xlsx de '14 CORREOS', consolida, convierte tipos y
    carga. Devuelve (filas_eliminadas, filas_insertadas_registro,
    filas_insertadas_bandejas). Levanta CorreosError ante cualquier fallo de
    SharePoint o SQL Server."""
    archivos = descargar_archivos(destino)
    registro_df, bandejas_df = consolidar(archivos)
    registro_df = preparar_registro(registro_df)
    bandejas_df = preparar_bandejas(bandejas_df)

    resultado = cargar(gateway, registro_df, bandejas_df, fecha_inicio, fecha_fin)
    logger.info(
        "Bronze finalizada. Registro: %s eliminadas / %s insertadas (periodo). Bandejas: %s insertadas (total).",
        *resultado,
    )
    return resultado
