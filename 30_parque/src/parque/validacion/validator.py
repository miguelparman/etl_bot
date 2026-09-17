"""Validacion: equivalente a la clausula 'WHERE periodo = ?' del Origen OLE
DB original (ahora aplicada sobre el DataFrame, porque el CSV de SharePoint
puede traer varios periodos mezclados) y a las disposiciones
'errorRowDisposition'/'truncationRowDisposition'='FailComponent' que tienen
TODAS las columnas del Origen/Destino OLE DB del .dtsx original: cualquier
valor que exceda el largo declarado aborta el Data Flow completo, no se
trunca en silencio ni se redirige a un sink de errores (el "error output" del
paquete original existe en la metadata pero no esta conectado a nada).
"""

from __future__ import annotations

import logging

import pandas as pd

import mappings
from exceptions import ValidacionError
from models import ParqueFlowSpec

logger = logging.getLogger("parque")


def validar_columnas(df: pd.DataFrame, spec: ParqueFlowSpec) -> None:
    faltantes = set(spec.nombres_columnas) - set(df.columns)
    if faltantes:
        raise ValidacionError(
            f"[{spec.nombre}] Faltan columnas esperadas en '{spec.archivo_csv}': {sorted(faltantes)}"
        )


def filtrar_periodo(df: pd.DataFrame, spec: ParqueFlowSpec, periodo: str) -> pd.DataFrame:
    """Equivalente a 'WHERE periodo = ?' del Origen OLE DB original."""
    filtrado = df[df[mappings.COLUMNA_PERIODO].astype("string") == str(periodo)].copy()
    logger.info(
        "[%s] %s de %s filas coinciden con periodo=%s",
        spec.nombre,
        len(filtrado),
        len(df),
        periodo,
    )
    return filtrado


def validar_longitudes(df: pd.DataFrame, spec: ParqueFlowSpec) -> None:
    """Equivalente a errorRowDisposition/truncationRowDisposition='FailComponent'
    en TODAS las columnas del Origen/Destino OLE DB original."""
    for columna in spec.columnas:
        valores = df[columna.nombre].astype("string")
        excede = valores.str.len() > columna.longitud_max
        if excede.any():
            filas = df.index[excede].tolist()
            raise ValidacionError(
                f"[{spec.nombre}] La columna '{columna.nombre}' excede el largo maximo "
                f"({columna.longitud_max} caracteres) en las filas {filas}; el componente "
                "OLE DB original aborta el Data Flow en este caso (FailComponent)."
            )


def validar(df: pd.DataFrame, spec: ParqueFlowSpec, periodo: str) -> pd.DataFrame:
    """Corre columnas -> filtro por periodo -> largos, en el mismo orden en
    que el .dtsx original aplicaba el filtro SQL antes de que el Data Flow
    viera las filas (los largos solo se validan sobre las filas que
    efectivamente se van a cargar)."""
    validar_columnas(df, spec)
    df_periodo = filtrar_periodo(df, spec, periodo)
    validar_longitudes(df_periodo, spec)
    return df_periodo
