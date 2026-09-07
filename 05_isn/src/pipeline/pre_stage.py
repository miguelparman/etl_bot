"""Equivalente a "SECUENCIA NUEVA" (parte 2: etapa TBL_ISN_PRE) del .dtsx original."""
from __future__ import annotations

import logging

from sqlalchemy import Engine

from src.database.connection import execute_script

logger = logging.getLogger("ssis_cl_isn")


def build_tbl_isn_pre(engine: Engine) -> None:
    """Secuencia "TBL_ISN_PRE": DROP + CREATE.

    Filtra candidatos elegibles (MOTIVO DE RETIRO IS NULL, ORDEN = 1),
    formatea RUT/ANI para el proveedor de encuestas y deduplica por
    RUT_CLIENTE (columna Indice).
    """
    with engine.begin() as conn:
        execute_script(conn, "09_drop_tbl_isn_pre.sql")
        execute_script(conn, "10_create_tbl_isn_pre.sql")
    logger.info("TBL_ISN_PRE reconstruida")


def consolidate_pre_history(engine: Engine) -> None:
    """Secuencia "Contenedor de secuencias 1": DELETE del snapshot de hoy +
    INSERT del snapshot actual de TBL_ISN_PRE en TBL_ISN_PRE_CONSOLIDADO."""
    with engine.begin() as conn:
        execute_script(conn, "11_consolidado_pre_delete_hoy.sql")
        execute_script(conn, "12_consolidado_pre_insert.sql")
    logger.info("TBL_ISN_PRE_CONSOLIDADO actualizada con el snapshot de hoy")
