"""Equivalente al contenedor "TBL_ISN_CALIDAD" del .dtsx original (rama
paralela B): DROP+CREATE TBL_ISN_CALIDAD -> "ACTUALIZACION SERVIDOR"
(DELETE hoy -> Data Flow de conversion+carga -> UPDATE FECHA DE CARGA)."""
from __future__ import annotations

import logging

from sqlalchemy import Engine

from src.config.settings import DatabaseSettings
from src.database.connection import execute_script, raw_connection
from src.extract.sql import read_query
from src.load.sqlserver import bulk_insert
from src.transform.type_casts import apply_envios_consolidado_casts
from src.utils.audit import RunAudit

logger = logging.getLogger("ssis_cl_isn")


def build_tbl_isn_calidad(engine: Engine) -> None:
    """Execute SQL Task "TBL_ISN_CALIDAD": DROP + SELECT INTO desde
    TBL_ISN_PRE (WHERE Indice = 1); misma proyeccion que TBL_ISN pero
    materializada en una tabla independiente para la carga de calidad."""
    with engine.begin() as conn:
        execute_script(conn, "16_drop_tbl_isn_calidad.sql")
        execute_script(conn, "17_create_tbl_isn_calidad.sql")
    logger.info("TBL_ISN_CALIDAD reconstruida")


def load_envios_consolidado(
    engine: Engine, db: DatabaseSettings, audit: RunAudit
) -> None:
    """Secuencia "ACTUALIZACION SERVIDOR":
    1) DELETE de hoy en CL_CALIDAD.TBL_ISN_ENVIOS_CONSOLIDADO
    2) Data Flow: TBL_ISN_CALIDAD -> casts -> carga masiva en TBL_ISN_ENVIOS_CONSOLIDADO
    3) UPDATE FECHA DE CARGA = hoy WHERE FECHA DE CARGA IS NULL
    """
    with engine.begin() as conn:
        execute_script(conn, "01_delete_envios_consolidado_hoy.sql")

    with engine.connect() as conn:
        df = read_query(conn, "18_select_tbl_isn_calidad_for_load.sql")
    audit.record_extracted("envios_consolidado", df.height)

    df = apply_envios_consolidado_casts(df)

    with raw_connection(db) as conn:
        inserted = bulk_insert(
            conn, df, "[CL_CALIDAD].[dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]"
        )
    audit.record_loaded("envios_consolidado", inserted)

    with engine.begin() as conn:
        execute_script(conn, "19_update_envios_consolidado_fecha_carga.sql")

    logger.info("TBL_ISN_ENVIOS_CONSOLIDADO actualizada: %s filas", inserted)
