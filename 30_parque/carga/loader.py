"""Carga.

Fase 1: TRUNCATE + Destino OLE DB (fast-load) de cada Data Flow 'PQ FIJO I' /
'PQ MOVIL I' del .dtsx original.

Fase 2: DELETE + Data Flow de 'PQ FIJO II' / 'PQ MOVIL II' (HISTORICO). A
diferencia del .dtsx original (que releia Externos_Frac con la misma
consulta que la sub-rama 'I'), aqui el Data Flow de HISTORICO se alimenta
desde la tabla _ACTUAL ya cargada por la Fase 1 (ver README, seccion
'Fase 2') -- por eso el INSERT se arma en Python a partir de
ParqueFlowSpec.nombres_columnas en vez de venir de un SELECT a SharePoint.
"""

from __future__ import annotations

import logging

import pandas as pd

import mappings
from db import DatabaseGateway
from models import ParqueFlowSpec

logger = logging.getLogger("parque")


def truncar_tabla(db: DatabaseGateway, spec: ParqueFlowSpec) -> None:
    """Tarea 'TRUNCATE' (PQ FIJO I / PQ MOVIL I)."""
    db.truncate_table(spec.tabla_destino)


def cargar_actual(db: DatabaseGateway, spec: ParqueFlowSpec, df: pd.DataFrame) -> int:
    """Destino OLE DB de 'TBL_PARQUE_FIJO_ACTUAL' / 'TBL_PARQUE_MOVIL_ACTUAL'."""
    return db.bulk_insert(spec.tabla_destino, df)


def borrar_historico_periodo(db: DatabaseGateway, spec: ParqueFlowSpec, periodo: str) -> int:
    """Tarea 'DELETE' (PQ FIJO II / PQ MOVIL II): purga el periodo vigente en
    _HISTORICO antes de reinsertarlo (delete-by-period + append). Devuelve la
    cantidad de filas purgadas."""
    filas = db.execute_script_rowcount(spec.sql_delete_historico, params=(periodo,))
    logger.info("[%s] %s filas purgadas de [dbo].[%s] (periodo=%s).", spec.nombre_historico, filas, spec.tabla_historico, periodo)
    return filas


def insertar_historico_desde_actual(db: DatabaseGateway, spec: ParqueFlowSpec, periodo: str) -> int:
    """Data Flow de 'PQ FIJO II' / 'PQ MOVIL II': en vez de releer el CSV/
    SharePoint, se alimenta desde la tabla _ACTUAL ya cargada por la Fase 1
    (mismo periodo que la DELETE previa acaba de purgar). Devuelve la
    cantidad de filas insertadas."""
    columnas_sql = ", ".join(f"[{c}]" for c in spec.nombres_columnas)
    insert_sql = (
        f"INSERT INTO [dbo].[{spec.tabla_historico}] ({columnas_sql}) "
        f"SELECT {columnas_sql} FROM [dbo].[{spec.tabla_destino}] "
        f"WHERE [{mappings.COLUMNA_PERIODO}] = ?"
    )
    filas = db.execute_script_rowcount(insert_sql, params=(periodo,))
    logger.info("[%s] %s filas insertadas en [dbo].[%s] desde [dbo].[%s].", spec.nombre_historico, filas, spec.tabla_historico, spec.tabla_destino)
    return filas
