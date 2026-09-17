"""Extraccion: SharePoint (CSV/Excel, carpeta '07 CROSS') -> DataFrame, un
extraer_xxx por Origen del .dtsx original. No filtra ni castea tipos -- eso
es responsabilidad de transformacion.py. Si normaliza mayusculas/minusculas
de encabezado (ver _normalizar_columnas): estos archivos son formularios/
planillas editados a mano por el negocio (Google Forms, Excel compartido),
no un esquema de base de datos -- un encabezado puede cambiar de casing sin
que el dato en si cambie (visto en produccion: 'segmento' en vez de
'Segmento' en 'Señalizaciones.csv'). validacion.py sigue siendo quien
decide si falta una columna de verdad."""

from __future__ import annotations

import logging

import pandas as pd

import mappings
from db import DatabaseGateway
from sharepoint.reader import SharePointCsvReader, SharePointExcelReader

logger = logging.getLogger("ventas")


def _normalizar_columnas(df: pd.DataFrame, nombres_esperados: tuple[str, ...]) -> pd.DataFrame:
    """Renombra las columnas de 'df' que coinciden con 'nombres_esperados'
    ignorando mayusculas/minusculas, a la forma exacta esperada -- sin tocar
    columnas que no coinciden con nada (p.ej. las que se descartan)."""
    mapa_lower = {nombre.lower(): nombre for nombre in nombres_esperados}
    renombre = {
        columna: mapa_lower[str(columna).lower()]
        for columna in df.columns
        if str(columna).lower() in mapa_lower and mapa_lower[str(columna).lower()] != columna
    }
    if renombre:
        logger.warning("Columnas normalizadas por casing distinto al esperado: %s", renombre)
        df = df.rename(columns=renombre)
    return df


def extraer_senhalizaciones(csv_reader: SharePointCsvReader) -> pd.DataFrame:
    """Origen Flat File 'Señalizaciones.csv' (Contenedor de secuencias 1 /
    Data Flow 'TBL_FUNNEL_SENHALIZACIONES')."""
    df = csv_reader.leer_csv(mappings.ARCHIVO_SENHALIZACIONES_CSV)
    esperadas = tuple(origen for origen, _destino in mappings.MAPEO_SENHALIZACIONES)
    df = _normalizar_columnas(df, esperadas)
    logger.info("[senalizaciones] '%s' leido: %s filas", mappings.ARCHIVO_SENHALIZACIONES_CSV, len(df))
    return df


def extraer_dni_senhalizaciones(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'DNI Senalizaciones$' (Contenedor de secuencias interno /
    Data Flow 'TBL_FUNNEL_SENHALIZACIONES_DNI')."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_SENHALIZACIONES_DNI)
    return _leer_hoja(excel_reader, mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_DNI_SENALIZACIONES, "senalizaciones", columnas)


def _leer_hoja(
    excel_reader: SharePointExcelReader, archivo: str, hoja: str, pipeline: str, columnas_esperadas: tuple[str, ...] = ()
) -> pd.DataFrame:
    df = excel_reader.leer_hoja(archivo, hoja)
    if columnas_esperadas:
        df = _normalizar_columnas(df, columnas_esperadas)
    logger.info("[%s] Hoja '%s' de '%s' leida: %s filas", pipeline, hoja, archivo, len(df))
    return df


# ---------------------------------------------------------------------------
# CROSS 0102 SSIS_CL_Ventas.dtsx
# ---------------------------------------------------------------------------


def extraer_ventas_basev2(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'baseV2$' (FUNNEL VENTAS V2.xlsx) / Data Flow 'TBL_FUNNEL_VENTAS_basev2_temp'."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_BASEV2)
    return _leer_hoja(excel_reader, mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_BASEV2, "ventas", columnas)


def extraer_ventas_esp(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'Esp$' (FUNNEL VENTAS V2.xlsx) / Data Flow 'TBL_FUNNEL_VENTAS_Esp_temp'."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_ESP)
    return _leer_hoja(excel_reader, mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_ESP, "ventas", columnas)


def extraer_ventas_sup(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'Sup$' (FUNNEL VENTAS V2.xlsx) / Data Flow 'TBL_FUNNEL_VENTAS_Sup_temp'."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_SUP)
    return _leer_hoja(excel_reader, mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_SUP, "ventas", columnas)


def extraer_ventas_rango_comisiones(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'Comisiones mes$' (Base Carta Meta.xlsx) / Data Flow 'TBL_VENTAS_RANGO_COMISIONES'."""
    return _leer_hoja(
        excel_reader, mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_COMISIONES_MES, "ventas",
        mappings.COLUMNAS_VENTAS_RANGO_COMISIONES,
    )


def extraer_ventas_dni_senhalizaciones(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'DNI Senalizaciones$' (Base Carta Meta.xlsx), recargado
    de forma independiente por Ventas ('Contenedor de secuencias 2\\Contenedor
    de secuencias 1') -- misma hoja/tabla que Señalizaciones, ver README."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_SENHALIZACIONES_DNI)
    return _leer_hoja(excel_reader, mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_DNI_SENALIZACIONES, "ventas", columnas)


def extraer_ventas_metas(excel_reader: SharePointExcelReader) -> pd.DataFrame:
    """Origen Excel 'Hoja1$' (Base Carta Meta.xlsx) / Data Flow 'METAS_COMISIONES'."""
    return _leer_hoja(
        excel_reader, mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_METAS, "ventas",
        mappings.COLUMNAS_VENTAS_METAS_ORIGEN,
    )


def extraer_ventas_basev2_temp(db: DatabaseGateway) -> pd.DataFrame:
    """Origen OLE DB 'LOCAL\\TBL_FUNNEL_VENTAS_Temp': lee TBL_FUNNEL_VENTAS_basev2_temp
    completa (AccessMode=0, sin filtro) para alimentar la Data Flow de 'LOCAL'."""
    df = db.read_table(mappings.TABLA_VENTAS_BASEV2_TEMP)
    logger.info("[ventas] [%s] leida: %s filas", mappings.TABLA_VENTAS_BASEV2_TEMP, len(df))
    return df
