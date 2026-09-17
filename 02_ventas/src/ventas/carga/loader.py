"""Carga: TRUNCATE/DELETE + Destino OLE DB (fast-load) de cada Data Flow del
.dtsx original."""

from __future__ import annotations

import logging

import pandas as pd

import mappings
import sql
from db import DatabaseGateway

logger = logging.getLogger("ventas")


def truncar_senhalizaciones(db: DatabaseGateway) -> None:
    """Execute SQL Task 'TRUNCATE SEÑALIZACIONES'."""
    db.execute_script(sql.SQL_TRUNCATE_SENHALIZACIONES)


def cargar_senhalizaciones(db: DatabaseGateway, df: pd.DataFrame) -> int:
    """Destino OLE DB de 'TBL_FUNNEL_SENHALIZACIONES'."""
    return db.bulk_insert(mappings.TABLA_SENHALIZACIONES, df)


def truncar_dni_senhalizaciones(db: DatabaseGateway) -> None:
    """Execute SQL Task 'TRUNCATE' (dentro de 'Contenedor de secuencias')."""
    db.execute_script(sql.SQL_TRUNCATE_SENHALIZACIONES_DNI)


def cargar_dni_senhalizaciones(db: DatabaseGateway, df: pd.DataFrame) -> int:
    """Destino OLE DB de 'TBL_FUNNEL_SENHALIZACIONES_DNI'."""
    return db.bulk_insert(mappings.TABLA_SENHALIZACIONES_DNI, df)


# ---------------------------------------------------------------------------
# CROSS 0102 SSIS_CL_Ventas.dtsx
# ---------------------------------------------------------------------------


def truncar_ventas_basev2(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_VENTAS_BASEV2_TEMP)


def cargar_ventas_basev2(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_VENTAS_BASEV2_TEMP, df)


def truncar_ventas_esp(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_VENTAS_ESP_TEMP)


def cargar_ventas_esp(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_VENTAS_ESP_TEMP, df)


def truncar_ventas_sup(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_VENTAS_SUP_TEMP)


def cargar_ventas_sup(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_VENTAS_SUP_TEMP, df)


def truncar_ventas_rango_comisiones(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_VENTAS_RANGO_COMISIONES)


def cargar_ventas_rango_comisiones(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_VENTAS_RANGO_COMISIONES, df)


def truncar_ventas_dni_senhalizaciones(db: DatabaseGateway) -> None:
    """Mismo TRUNCATE que Señalizaciones, pero disparado por el paquete de
    Ventas (Contenedor de secuencias 2\\Contenedor de secuencias 1)."""
    db.execute_script(sql.SQL_TRUNCATE_SENHALIZACIONES_DNI)


def cargar_ventas_dni_senhalizaciones(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_SENHALIZACIONES_DNI, df)


def truncar_metas_comisiones(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_METAS_COMISIONES)


def cargar_metas_comisiones(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_METAS_COMISIONES, df)


def truncar_ventas_temp(db: DatabaseGateway) -> None:
    db.execute_script(sql.SQL_TRUNCATE_VENTAS_TEMP)


def cargar_ventas_temp(db: DatabaseGateway, df: pd.DataFrame) -> int:
    return db.bulk_insert(mappings.TABLA_VENTAS_TEMP, df)
