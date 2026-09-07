"""Carga: truncados, inserciones y la copia entre bases de datos de
CL_Proc_Carga_Cartera.dtsx (Destinos OLE DB de ambos Data Flows, mas la
tarea final 'CARGA' del historico).
"""

from __future__ import annotations

import logging

import pandas as pd

from app.application import mappings, sql
from app.application.ports import DatabaseGateway
from app.domain.exceptions import CargaError

logger = logging.getLogger("cartera")


def truncar_staging(db_temporales: DatabaseGateway) -> None:
    """Tarea 'CARGA CARTERA TEMPORAL / TRUNCA TABLA'."""
    db_temporales.truncate_table(mappings.TABLA_STAGING)


def cargar_staging(db_temporales: DatabaseGateway, df: pd.DataFrame) -> int:
    """Destino OLE DB 'TBL_CARTERA TEMP' del Data Flow 1."""
    return db_temporales.bulk_insert(mappings.TABLA_STAGING, df)


def truncar_actual(db_cartera: DatabaseGateway) -> None:
    """Tarea 'CARGA CARTERA ACTUAL / TRUNCA TABLA'."""
    db_cartera.truncate_table(mappings.TABLA_ACTUAL)


def copiar_temporal_a_actual(
    db_temporales: DatabaseGateway, db_cartera: DatabaseGateway
) -> int:
    """Data Flow 2 'ALIMENTA TABLA': copia TBL_CARTERA (CL_TEMPORALES) hacia
    TBL_CARTERA_ACTUAL (CL_CARTERA), seleccionando y renombrando columnas tal
    como lo hacia el mapeo del Destino OLE DB original."""
    try:
        df = db_temporales.read_table(mappings.TABLA_STAGING)
        df = df[list(mappings.ACTUAL_SOURCE_COLUMNS)].rename(columns=mappings.ACTUAL_COLUMN_RENAME)
        return db_cartera.bulk_insert(mappings.TABLA_ACTUAL, df)
    except Exception as exc:
        raise CargaError(f"Fallo 'ALIMENTA TABLA' (copiar_temporal_a_actual): {exc}") from exc


def insertar_historico(db_cartera: DatabaseGateway) -> None:
    """Tarea 'CARGA': INSERT posicional del periodo vigente en
    TBL_HISTORIAL_CARTERA, mas el UPDATE de 'ing_sspp' desde TBL_CARTERA_ACTUAL."""
    try:
        db_cartera.execute_script(sql.CARGA_HISTORICO)
    except Exception as exc:
        raise CargaError(f"Fallo 'CARGA' (insertar_historico): {exc}") from exc
    logger.info("CARGA: periodo vigente insertado en TBL_HISTORIAL_CARTERA.")
