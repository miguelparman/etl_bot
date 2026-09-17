"""Validacion: controles de calidad de datos equivalentes a las
disposiciones 'errorRowDisposition'/'truncationRowDisposition' de los
componentes Origen/Data Convert/Destino OLE DB de los .dtsx originales.

Cada .dtsx tiene DOS capas de disposicion sobre una misma columna (Origen ->
Data Convert), pero en la practica solo una es realmente disparable en
Python:

- Columnas de TEXTO: el Data Convert es 'FailComponent' en (casi) todas --
  exceder el ancho declarado debe abortar el Data Flow completo, no
  truncarse en silencio. Se valida aqui, sobre las columnas YA renombradas
  al nombre de destino (ver transformacion.py).
- Columnas NUMERICAS/FECHA: el Origen Flat File/Excel ya es 'IgnoreFailure'
  para estas (un valor invalido se descarta sin abortar) y el Data Convert
  no puede fallar sobre un valor que ya llego tipado -- se manejan como
  coerce a NULL en transformacion.py, no como un ValidacionError aqui.
"""

from __future__ import annotations

import logging

import pandas as pd

import mappings
from exceptions import ValidacionError

logger = logging.getLogger("ventas")


def validar_columnas_presentes(df: pd.DataFrame, columnas_esperadas: tuple[str, ...], origen: str) -> None:
    faltantes = set(columnas_esperadas) - set(df.columns)
    if faltantes:
        raise ValidacionError(f"Faltan columnas esperadas en '{origen}': {sorted(faltantes)}")


def validar_columnas_senhalizaciones(df: pd.DataFrame) -> None:
    """Equivalente a la validacion de esquema del Origen Flat File
    'Señalizaciones.csv'."""
    columnas_csv = tuple(origen for origen, _destino in mappings.MAPEO_SENHALIZACIONES)
    validar_columnas_presentes(df, columnas_csv, mappings.ARCHIVO_SENHALIZACIONES_CSV)


def validar_columnas_dni_senhalizaciones(df: pd.DataFrame) -> None:
    """Equivalente a la validacion de esquema del Origen Excel 'DNI Senalizaciones$'."""
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_SENHALIZACIONES_DNI)
    validar_columnas_presentes(df, columnas, f"{mappings.ARCHIVO_BASE_CARTA_META_XLSX}!{mappings.HOJA_DNI_SENALIZACIONES}")


def validar_longitudes(df: pd.DataFrame, columnas: tuple, contexto: str) -> None:
    """Equivalente a errorRowDisposition/truncationRowDisposition='FailComponent'
    del Data Convert: solo se aplica a las columnas marcadas 'estricto=True'
    (columnas de texto -- las numericas/fecha usan longitud_max=0/estricto=False
    y se manejan aparte en transformacion.py)."""
    for columna in columnas:
        if not columna.estricto or columna.longitud_max <= 0:
            continue
        valores = df[columna.nombre].astype("string")
        excede = valores.str.len() > columna.longitud_max
        if excede.any():
            filas = df.index[excede].tolist()
            raise ValidacionError(
                f"[{contexto}] La columna '{columna.nombre}' excede el largo maximo "
                f"({columna.longitud_max} caracteres) en las filas {filas}; el Data Convert "
                "original aborta el Data Flow en este caso (FailComponent)."
            )


def validar_longitudes_senhalizaciones(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_SENHALIZACIONES, "TBL_FUNNEL_SENHALIZACIONES")


def validar_longitudes_dni_senhalizaciones(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_SENHALIZACIONES_DNI, "TBL_FUNNEL_SENHALIZACIONES_DNI")


# ---------------------------------------------------------------------------
# CROSS 0102 SSIS_CL_Ventas.dtsx
# ---------------------------------------------------------------------------


def validar_columnas_ventas_basev2(df: pd.DataFrame) -> None:
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_BASEV2)
    validar_columnas_presentes(df, columnas, f"{mappings.ARCHIVO_FUNNEL_VENTAS_XLSX}!{mappings.HOJA_BASEV2}")


def validar_columnas_ventas_esp(df: pd.DataFrame) -> None:
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_ESP)
    validar_columnas_presentes(df, columnas, f"{mappings.ARCHIVO_FUNNEL_VENTAS_XLSX}!{mappings.HOJA_ESP}")


def validar_columnas_ventas_sup(df: pd.DataFrame) -> None:
    columnas = tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_SUP)
    validar_columnas_presentes(df, columnas, f"{mappings.ARCHIVO_FUNNEL_VENTAS_XLSX}!{mappings.HOJA_SUP}")


def validar_columnas_ventas_rango_comisiones(df: pd.DataFrame) -> None:
    """El Data Flow original no tiene Data Convert (columnas pasan directo,
    sin cast) -- solo se valida que el origen tenga las columnas esperadas."""
    validar_columnas_presentes(
        df, mappings.COLUMNAS_VENTAS_RANGO_COMISIONES, f"{mappings.ARCHIVO_BASE_CARTA_META_XLSX}!{mappings.HOJA_COMISIONES_MES}"
    )


def validar_columnas_ventas_metas(df: pd.DataFrame) -> None:
    validar_columnas_presentes(
        df, mappings.COLUMNAS_VENTAS_METAS_ORIGEN, f"{mappings.ARCHIVO_BASE_CARTA_META_XLSX}!{mappings.HOJA_METAS}"
    )


def validar_longitudes_ventas_basev2(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_VENTAS_BASEV2, mappings.TABLA_VENTAS_BASEV2_TEMP)


def validar_longitudes_ventas_esp(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_VENTAS_ESP, mappings.TABLA_VENTAS_ESP_TEMP)


def validar_longitudes_ventas_sup(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_VENTAS_SUP, mappings.TABLA_VENTAS_SUP_TEMP)


def validar_longitudes_ventas_metas(df: pd.DataFrame) -> None:
    validar_longitudes(df, mappings.COLUMNAS_VENTAS_METAS_TEXTO, mappings.TABLA_METAS_COMISIONES)
