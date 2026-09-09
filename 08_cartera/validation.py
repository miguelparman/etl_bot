"""Validacion: tarea 'VALIDA' de CL_Proc_Carga_Cartera.dtsx (Sequence
'CARGA CARTERA TEMPORAL').

En el .dtsx original eran 4 bloques 'IF EXISTS (...) BEGIN RAISERROR(...) END'
dentro de un unico Execute SQL Task: si el primero fallaba, SSIS abortaba el
paquete sin evaluar los siguientes (severidad 16 corta la ejecucion). Aqui se
replica el mismo orden y el mismo comportamiento de "corto-circuito": se
evalua cada control en secuencia y se aborta con ValidacionError en el
primero que falle, sin evaluar los restantes.
"""

from __future__ import annotations

import logging

import sql
from db import DatabaseGateway
from exceptions import ValidacionError

logger = logging.getLogger("cartera")

_CONTROLES: tuple[tuple[str, str], ...] = (
    (sql.VALIDA_RUT_DUPLICADO, sql.MSG_RUT_DUPLICADO),
    (sql.VALIDA_ASESOR_NO_ASIGNADO, sql.MSG_ASESOR_NO_ASIGNADO),
    (sql.VALIDA_RUT_NO_ASIGNADO, sql.MSG_RUT_NO_ASIGNADO),
    (sql.VALIDA_NOMBRE_NO_ASIGNADO, sql.MSG_NOMBRE_NO_ASIGNADO),
)


def validar_cartera_temporal(db_temporales: DatabaseGateway) -> None:
    """Corre los 4 controles de calidad sobre CL_TEMPORALES.dbo.TBL_CARTERA."""
    for consulta, mensaje in _CONTROLES:
        cantidad = db_temporales.fetch_scalar(consulta)
        if cantidad:
            raise ValidacionError(mensaje)
    logger.info("VALIDA: los 4 controles de calidad pasaron correctamente.")
