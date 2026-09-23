"""Lee y consolida las hojas 'Registro' y 'Bandejas' de los .xlsx de
'14 CORREOS' (ya copiados desde 'BPO' por copiar_correos.py).

Cada hoja 'Registro' es una plantilla PRE-FORMATEADA a 5000 filas: solo una
fraccion tiene datos reales (el resto tiene 'Bandeja' vacio) -- se descartan
antes de consolidar, si no se cargarian miles de filas vacias por archivo.
Un archivo con una hoja faltante o con columnas faltantes se omite (se
registra el motivo) en vez de abortar todo el proceso.
"""

from __future__ import annotations

import io
import logging

import pandas as pd

from logging_setup import NOMBRE_LOGGER
from mappings import (
    COLUMNA_CLAVE_BANDEJAS,
    COLUMNA_CLAVE_REGISTRO,
    COLUMNA_DEDUP_REGISTRO,
    COLUMNA_ORIGEN,
    COLUMNAS_BANDEJAS,
    COLUMNAS_REGISTRO,
)

logger = logging.getLogger(NOMBRE_LOGGER)

# Excel cuenta los dias desde este origen (dia 0 = 1899-12-30, convencion
# historica de Excel/Lotus 1-2-3) -- 'FechaHora' llega como este serial
# (hora LOCAL Peru/Bogota, UTC-5), no como celda con formato de fecha.
_ORIGEN_FECHA_EXCEL = "1899-12-30"


def _leer_hoja(
    contenido: bytes, nombre_archivo: str, hoja: str, columnas_esperadas: list[str], columna_clave: str
) -> pd.DataFrame | None:
    """Lee una hoja y valida su estructura. Devuelve None (con el motivo
    registrado en el log) si la hoja no existe o le faltan columnas
    esperadas -- ese archivo/hoja se omite, no detiene el resto."""
    try:
        df = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja)
    except ValueError:
        logger.error("'%s': no tiene la hoja '%s', se omite.", nombre_archivo, hoja)
        return None

    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        logger.error("'%s'/'%s': faltan columnas %s, se omite.", nombre_archivo, hoja, faltantes)
        return None

    df = df[columnas_esperadas].copy()
    return df[df[columna_clave].notna()]


def consolidar(archivos: dict[str, bytes]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Consolida 'Registro' y 'Bandejas' de todos los archivos, de forma
    independiente (nunca se mezclan). A cada fila de ambas hojas se le agrega
    'ORIGEN' con el nombre del .xlsx del que proviene. Aplica una
    deduplicacion defensiva por 'ID_Mensaje' sobre 'Registro' antes de
    devolverlo (ante un duplicado se conserva la fila, y su 'ORIGEN', del
    primer archivo)."""
    registros: list[pd.DataFrame] = []
    bandejas: list[pd.DataFrame] = []

    for nombre, contenido in archivos.items():
        registro_df = _leer_hoja(contenido, nombre, "Registro", COLUMNAS_REGISTRO, COLUMNA_CLAVE_REGISTRO)
        if registro_df is not None:
            registro_df[COLUMNA_ORIGEN] = nombre
            registros.append(registro_df)

        bandejas_df = _leer_hoja(contenido, nombre, "Bandejas", COLUMNAS_BANDEJAS, COLUMNA_CLAVE_BANDEJAS)
        if bandejas_df is not None:
            bandejas_df[COLUMNA_ORIGEN] = nombre
            bandejas.append(bandejas_df)

    registro_total = (
        pd.concat(registros, ignore_index=True)
        if registros
        else pd.DataFrame(columns=[*COLUMNAS_REGISTRO, COLUMNA_ORIGEN])
    )
    bandejas_total = (
        pd.concat(bandejas, ignore_index=True)
        if bandejas
        else pd.DataFrame(columns=[*COLUMNAS_BANDEJAS, COLUMNA_ORIGEN])
    )

    antes = len(registro_total)
    registro_total = registro_total.drop_duplicates(subset=[COLUMNA_DEDUP_REGISTRO], keep="first")
    if len(registro_total) < antes:
        logger.warning(
            "%s fila(s) de 'Registro' descartadas por '%s' duplicado.",
            antes - len(registro_total),
            COLUMNA_DEDUP_REGISTRO,
        )

    logger.info(
        "Consolidado: %s fila(s) de 'Registro', %s fila(s) de 'Bandejas' (%s archivo(s)).",
        len(registro_total),
        len(bandejas_total),
        len(archivos),
    )
    return registro_total, bandejas_total


def preparar_registro(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte los campos de fecha de 'Registro' a tipos reales:

    - 'FechaHora_UTC_Texto' (texto ISO-8601 UTC, p.ej.
      '2026-09-17T08:59:36.0000000+00:00') -> datetime naive en UTC. Es el
      campo de control de carga incremental (ver mappings.COLUMNA_CONTROL_FECHA).
    - 'FechaHora' (serial de Excel en hora local Peru/Bogota) -> datetime.

    Una fila cuyo 'FechaHora_UTC_Texto' no se pueda interpretar como fecha se
    descarta (no se puede ubicar en ningun periodo de carga) y queda
    registrada en el log."""
    df = df.copy()

    utc = pd.to_datetime(df["FechaHora_UTC_Texto"], utc=True, errors="coerce")
    invalidas = int(utc.isna().sum() - df["FechaHora_UTC_Texto"].isna().sum())
    if invalidas > 0:
        logger.warning(
            "%s fila(s) con '%s' invalido, se descartan (no se pueden ubicar en un periodo).",
            invalidas,
            "FechaHora_UTC_Texto",
        )
    df["FechaHora_UTC_Texto"] = utc.dt.tz_convert(None)
    df = df[df["FechaHora_UTC_Texto"].notna()]

    df["FechaHora"] = _convertir_fecha_hora(df["FechaHora"])

    return df


def _convertir_fecha_hora(serie: pd.Series) -> pd.Series:
    """'FechaHora' llega normalmente como serial de Excel (float, hora local
    Peru/Bogota) pero en datos reales se observo que, cuando alguna celda del
    origen tenia formato de fecha aplicado (en vez de numero plano), pandas
    ya la entrega como datetime -- mezclando ambos tipos en la misma columna
    al consolidar varios archivos (dtype 'object'). Se convierte cada valor
    segun corresponda: numerico -> epoch de Excel; ya-datetime -> se
    conserva tal cual; cualquier otra cosa (vacio, texto no numerico) -> NaT."""
    numerico = pd.to_numeric(serie, errors="coerce")
    desde_numero = pd.to_datetime(numerico, unit="D", origin=_ORIGEN_FECHA_EXCEL, errors="coerce")
    desde_datetime = pd.to_datetime(serie, errors="coerce")
    return desde_numero.where(desde_numero.notna(), desde_datetime)


def preparar_bandejas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte 'UltimaRevisionEntrada'/'UltimaRevisionSalida' (texto
    ISO-8601 UTC) a datetime naive en UTC. A diferencia de 'Registro', una
    fecha invalida aqui NO descarta la fila (TBL_CORREO_BANDEJAS es un
    reemplazo completo, no filtrado por periodo) -- queda como NULL."""
    df = df.copy()
    for columna in ("UltimaRevisionEntrada", "UltimaRevisionSalida"):
        df[columna] = pd.to_datetime(df[columna], utc=True, errors="coerce").dt.tz_convert(None)
    return df
