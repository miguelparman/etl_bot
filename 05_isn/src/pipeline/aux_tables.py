"""Equivalente al "Contenedor de secuencias" de nivel superior del .dtsx
original: 4 pasos SIN restricciones de precedencia entre si (se ejecutaban en
paralelo en SSIS). Ver src/main.py para la orquestacion concurrente."""
from __future__ import annotations

import logging

from sqlalchemy import Engine

from src.config.settings import DatabaseSettings, FilePathSettings
from src.database.connection import execute_script, raw_connection
from src.extract.csv_source import read_aux_cliente, read_aux_contacto
from src.load.sqlserver import bulk_insert
from src.utils.audit import RunAudit

logger = logging.getLogger("ssis_cl_isn")


def delete_envios_consolidado_hoy(engine: Engine) -> None:
    """Execute SQL Task "DELETE ENVIOS_CONSOLIDADO (LOCAL)"."""
    with engine.begin() as conn:
        execute_script(conn, "01_delete_envios_consolidado_hoy.sql")
    logger.info("DELETE ENVIOS_CONSOLIDADO (LOCAL) ejecutado")


def rebuild_reference_tables(engine: Engine) -> None:
    """Execute SQL Task "TBLS AUXILIARES" (TERMOMETRO + 3 tablas CCAA)."""
    with engine.begin() as conn:
        execute_script(conn, "02_rebuild_tablas_auxiliares.sql")
    logger.info("Tablas auxiliares (TERMOMETRO/CCAA) reconstruidas")


def load_aux_contacto(
    engine: Engine, db: DatabaseSettings, paths: FilePathSettings, audit: RunAudit
) -> None:
    """Secuencia "TBL_ISN_AUX_CONTACTO 1": TRUNCATE + carga de
    Reporte_isn_aux_contacto_v2.csv en TBL_ISN_SF_AUX_CONTACTO."""
    with engine.begin() as conn:
        execute_script(conn, "03_truncate_aux_contacto.sql")

    df = read_aux_contacto(paths.aux_contacto_csv)
    audit.record_extracted("aux_contacto", df.height)

    with raw_connection(db) as conn:
        inserted = bulk_insert(conn, df, "[CL_ISN].[dbo].[TBL_ISN_SF_AUX_CONTACTO]")
    audit.record_loaded("aux_contacto", inserted)
    logger.info("TBL_ISN_SF_AUX_CONTACTO recargada: %s filas", inserted)


def load_aux_cliente(
    engine: Engine, db: DatabaseSettings, paths: FilePathSettings, audit: RunAudit
) -> None:
    """Secuencia "TBL_ISN_SF_AUX_CLIENTE 1": TRUNCATE + carga de
    Reporte_isn_aux_cliente_v2.csv en TBL_ISN_SF_AUX_CLIENTE."""
    with engine.begin() as conn:
        execute_script(conn, "04_truncate_aux_cliente.sql")

    df = read_aux_cliente(paths.aux_cliente_csv)
    audit.record_extracted("aux_cliente", df.height)

    with raw_connection(db) as conn:
        inserted = bulk_insert(conn, df, "[CL_ISN].[dbo].[TBL_ISN_SF_AUX_CLIENTE]")
    audit.record_loaded("aux_cliente", inserted)
    logger.info("TBL_ISN_SF_AUX_CLIENTE recargada: %s filas", inserted)
