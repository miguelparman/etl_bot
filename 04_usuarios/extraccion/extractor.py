"""Extraccion: un extraer_xxx(db, periodo) por cada Origen OLE DB
parametrizado ('SQL Command') de los 5 paquetes USUARIOS_*.dtsx."""

from __future__ import annotations

import logging

import pandas as pd

import mappings
import sql
from db import DatabaseGateway
from exceptions import ExtraccionError
from models import Periodo

logger = logging.getLogger("usuarios")


def extraer_parque(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB '55_PARQUE' del Data Flow 'PARQUE'
    (USUARIOS_0101 Parque.dtsx). Los 3 parametros posicionales del query
    original estaban los 3 enlazados a User::Periodo."""
    try:
        return db_externos_frac.run_query(sql.PARQUE_SELECT, params=(periodo.valor, periodo.valor, periodo.valor))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB '55_PARQUE': {exc}") from exc


def extraer_bajas_fraude(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB 'BAJAS_FRAUDE 233' del Data Flow
    'TBL_SERVCH_BAJAS_FRAUDE' (USUARIOS_0201 SSIS_CL_Retenciones.dtsx)."""
    try:
        return db_externos_frac.run_query(sql.RETENCIONES_BAJAS_FRAUDE_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB 'BAJAS_FRAUDE 233': {exc}") from exc


def extraer_bajas_por_alta(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB '223_BAJAS_POR_ALTA_FO' del Data Flow
    'TBL_SERVCH_BAJAS_POR_ALTA_FO' (USUARIOS_0201 SSIS_CL_Retenciones.dtsx)."""
    try:
        return db_externos_frac.run_query(sql.RETENCIONES_BAJAS_POR_ALTA_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB '223_BAJAS_POR_ALTA_FO': {exc}") from exc


def extraer_bd_reten(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB 'BD_RETEN_V2 (223)' + componente 'Data Conversion' del
    Data Flow 'BD_RETEN' (USUARIOS_0201 SSIS_CL_Retenciones.dtsx)."""
    try:
        df = db_externos_frac.run_query(sql.RETENCIONES_BD_RETEN_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB 'BD_RETEN_V2 (223)': {exc}") from exc
    return _aplicar_conversion_bd_reten(df)


def _aplicar_conversion_bd_reten(df: pd.DataFrame) -> pd.DataFrame:
    # Componente 'Data Conversion': 'ROWNO' (solo usado en el WHERE ROWNO=1
    # de la consulta) y 'motivo' (seleccionado en el CTE pero sin columna de
    # salida "Copy of ...") no llegan al destino.
    df = df.drop(columns=list(mappings.BD_RETEN_COLUMNAS_DESCARTADAS), errors="ignore").copy()

    # 'Evaluacion' llega como literal entero 1 (desde el CTE) y el
    # componente lo convierte a string(5).
    df["Evaluacion"] = df["Evaluacion"].astype(str)
    # 'last_modified' (alias de fecha_ultima_actualizacion) se convierte de
    # datetime a date (sin componente de hora).
    df["last_modified"] = pd.to_datetime(df["last_modified"]).dt.date

    # errorRowDisposition="FailComponent" (comportamiento por defecto, igual
    # que en 08_cartera): un valor que excede el ancho debe abortar la
    # extraccion, no truncarse en silencio.
    for columna, largo in mappings.BD_RETEN_TRUNCATION_LENGTHS.items():
        valores = df[columna].astype("string")
        excede = valores.str.len() > largo
        if excede.any():
            filas = df.index[excede].tolist()
            raise ExtraccionError(
                f"La columna '{columna}' excede el ancho de truncamiento ({largo} caracteres) "
                f"en las filas {filas} del Data Flow 'BD_RETEN' (Data Conversion, "
                "errorRowDisposition=FailComponent)."
            )
        df[columna] = valores.str.slice(0, largo)
    return df


def extraer_bajas_fijo(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB del pipe 'BAJAS_FIJO' del Data Flow 'TBL_CH_BAJAS'
    (USUARIOS_0300 ETL_INTENCIONES.dtsx)."""
    try:
        return db_externos_frac.run_query(sql.INTENCIONES_BAJAS_FIJO_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB 'BAJAS_FIJO': {exc}") from exc


def extraer_bajas_movil(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB del pipe 'BAJAS_MOVIL' del Data Flow 'TBL_CH_BAJAS'
    (USUARIOS_0300 ETL_INTENCIONES.dtsx)."""
    try:
        return db_externos_frac.run_query(sql.INTENCIONES_BAJAS_MOVIL_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB 'BAJAS_MOVIL': {exc}") from exc


def extraer_usuarios_retenciones(db_cl_usuarios: DatabaseGateway) -> pd.DataFrame:
    """Origen OLE DB del Data Flow 'CARGA DE USUARIOS RETENCIONES SERVIDOR
    CHILE' (USUARIOS_0300 ETL_INTENCIONES.dtsx). Sin parametros."""
    try:
        return db_cl_usuarios.run_query(sql.INTENCIONES_USUARIOS_RETENCIONES_SELECT)
    except Exception as exc:
        raise ExtraccionError(
            f"Fallo el Origen OLE DB de 'CARGA DE USUARIOS RETENCIONES SERVIDOR CHILE': {exc}"
        ) from exc


def extraer_intenciones_v2(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB + componente 'Data Conversion 1' del Data Flow
    'INTENCIONES' (USUARIOS_0300 ETL_INTENCIONES.dtsx). El Destino OLE DB
    'INTENCIONES LOCAL' (carga/loader.cargar_intenciones_local) es el que
    tiene disposicion de error IgnoreFailure, no este componente."""
    try:
        df = db_externos_frac.run_query(sql.INTENCIONES_V2_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB de 'INTENCIONES': {exc}") from exc
    return _aplicar_conversion_intenciones_v2(df)


def _aplicar_conversion_intenciones_v2(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for columna, largo in mappings.INTENCIONES_V2_TRUNCATION_LENGTHS.items():
        valores = df[columna].astype("string")
        excede = valores.str.len() > largo
        if excede.any():
            filas = df.index[excede].tolist()
            raise ExtraccionError(
                f"La columna '{columna}' excede el ancho de truncamiento ({largo} caracteres) "
                f"en las filas {filas} del Data Flow 'INTENCIONES' (Data Conversion 1, "
                "errorRowDisposition=FailComponent)."
            )
        df[columna] = valores.str.slice(0, largo)
    return df


def extraer_item_amdocs(db_externos_frac: DatabaseGateway, periodo: Periodo) -> pd.DataFrame:
    """Origen OLE DB + componente 'Data Conversion' del Data Flow
    'INTEN_AMDOCS' (USUARIOS_0301 SSIS_CL_Item_amdocs.dtsx). A diferencia de
    BD_RETEN/INTENCIONES_V2, este componente tiene disposicion de error
    IgnoreFailure: los casteos son tolerantes (nunca abortan la fila, ver
    mappings.py)."""
    try:
        df = db_externos_frac.run_query(sql.ITEM_AMDOCS_SELECT, params=(periodo.valor,))
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB de 'INTEN_AMDOCS': {exc}") from exc
    return _aplicar_conversion_item_amdocs(df)


def _aplicar_conversion_item_amdocs(df: pd.DataFrame) -> pd.DataFrame:
    # 'rutcli' se convierte pero nunca se mapea al destino; 'ROWNO' (siempre
    # 1, dado el filtro ROWNO=1 del origen) se mapea a la columna 'Evaluacion'.
    df = df.drop(columns=list(mappings.ITEM_AMDOCS_COLUMNAS_DESCARTADAS), errors="ignore").copy()
    df = df.rename(columns=mappings.ITEM_AMDOCS_RENOMBRES)

    # errorRowDisposition="IgnoreFailure": un valor que no castea no aborta
    # la fila, queda NULL -- a diferencia de BD_RETEN/INTENCIONES_V2.
    for columna in mappings.ITEM_AMDOCS_INT_COLUMNS:
        df[columna] = pd.to_numeric(df[columna], errors="coerce").astype("Int64")
    for columna in mappings.ITEM_AMDOCS_DATETIME_COLUMNS:
        df[columna] = pd.to_datetime(df[columna], errors="coerce")
    for columna, largo in mappings.ITEM_AMDOCS_TRUNCATION_LENGTHS.items():
        df[columna] = df[columna].astype("string").str.slice(0, largo)
    return df


def extraer_saip(db_externos_frac: DatabaseGateway) -> pd.DataFrame:
    """Origen OLE DB '223 SAIP' + componente 'Conversion de datos' del Data
    Flow 'SAIP' (USUARIOS_0302 ETL_BASE_SAIP.dtsx). Sin parametros -- unico
    de los 5 paquetes sin variable de periodo."""
    try:
        df = db_externos_frac.run_query(sql.SAIP_SELECT)
    except Exception as exc:
        raise ExtraccionError(f"Fallo el Origen OLE DB '223 SAIP': {exc}") from exc
    return _aplicar_conversion_saip(df)


def _aplicar_conversion_saip(df: pd.DataFrame) -> pd.DataFrame:
    # 'fec_saip_a'/'fec_saip_b' se seleccionan pero nunca llegan al destino.
    df = df.drop(columns=list(mappings.SAIP_COLUMNAS_DESCARTADAS), errors="ignore").copy()
    try:
        # 'fec_ingr' es un valor de fecha nativo devuelto por pyodbc (columna
        # SQL Server sin formatear). 'FECHA' llega como texto 'dd/MM/yyyy'
        # (formateada asi en el propio query, ver sql.SAIP_SELECT) -- cada
        # una necesita su propio parseo para no ser ambigua.
        df["fec_ingr"] = pd.to_datetime(df["fec_ingr"]).dt.date
        df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True).dt.date
    except Exception as exc:
        raise ExtraccionError(
            f"No se pudieron convertir a fecha las columnas ('fec_ingr', 'FECHA') "
            f"del Data Flow 'SAIP' (Conversion de datos): {exc}"
        ) from exc
    return df
