"""Equivalente a "SECUENCIA NUEVA" (parte 1: etapa SF) del .dtsx original.

Orden estricto original (con restricciones de precedencia reales):
SF -> Contenedor de secuencias (historico SF) -> TBL_ISN_PRE -> Contenedor de
secuencias 1 (historico PRE). Este modulo cubre la etapa SF; pre_stage.py
cubre TBL_ISN_PRE y su historico.
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import Engine

from src.database.connection import execute_script

logger = logging.getLogger("ssis_cl_isn")


def build_tbl_isn_sf(engine: Engine, fecha_inicio: date, fecha_fin: date) -> None:
    """Secuencia "SF": DROP + CREATE de TBL_ISN_SF.

    Contiene la consulta de negocio mas critica del paquete (18 LEFT JOIN +
    calculo de MOTIVO DE RETIRO). Se ejecuta tal cual desde
    sql/06_create_tbl_isn_sf.sql, parametrizada de forma segura (sin
    interpolar fechas en el texto SQL).
    """
    with engine.begin() as conn:
        execute_script(conn, "05_drop_tbl_isn_sf.sql")
        execute_script(
            conn,
            "06_create_tbl_isn_sf.sql",
            {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
        )
    logger.info(
        "TBL_ISN_SF reconstruida para el rango %s..%s", fecha_inicio, fecha_fin
    )


def consolidate_sf_history(engine: Engine) -> None:
    """Secuencia "Contenedor de secuencias" (dentro de SECUENCIA NUEVA):
    DELETE del snapshot de hoy + INSERT del snapshot actual de TBL_ISN_SF
    en TBL_ISN_SF_CONSOLIDADO (tabla historica/auditoria)."""
    with engine.begin() as conn:
        execute_script(conn, "07_consolidado_sf_delete_hoy.sql")
        execute_script(conn, "08_consolidado_sf_insert.sql")
    logger.info("TBL_ISN_SF_CONSOLIDADO actualizada con el snapshot de hoy")
