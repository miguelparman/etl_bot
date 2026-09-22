"""Acceso a SQL Server ('CL_MOVIL', 172.17.0.162): fabrica de conexiones
(pyodbc) y el gateway usado por cargar_correos.py para eliminar por rango,
truncar e insertar. Mismo patron ya usado en 02_ventas/src/ventas/db.py y
08_cartera/src/cartera/db.py."""

from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np
import pandas as pd
import pyodbc

from config import DbSettings
from exceptions import CargaError
from logging_setup import NOMBRE_LOGGER

logger = logging.getLogger(NOMBRE_LOGGER)


def _fila_a_parametros(fila: tuple) -> tuple:
    """Sanea una fila (tupla de valores de un DataFrame) antes de bindear los
    parametros del INSERT contra pyodbc: NaN/NaT -> None (pyodbc no puede
    bindear un NaN crudo), numpy.generic -> tipo nativo de Python (pyodbc no
    sabe describir un numpy.int64/float64)."""
    saneada = []
    for valor in fila:
        if pd.isna(valor):
            saneada.append(None)
        elif isinstance(valor, np.generic):
            saneada.append(valor.item())
        else:
            saneada.append(valor)
    return tuple(saneada)


def crear_conexion(settings: DbSettings) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{settings.driver}}};"
        f"SERVER={settings.server};"
        f"DATABASE={settings.database};"
        f"UID={settings.user};"
        f"PWD={settings.password};"
        f"Encrypt={settings.encrypt};"
        f"TrustServerCertificate={settings.trust_server_certificate}"
    )
    return pyodbc.connect(conn_str)


class DatabaseGateway:
    def __init__(self, conn: pyodbc.Connection, batch_size: int = 5000) -> None:
        self._conn = conn
        self._batch_size = batch_size

    def execute_script_rowcount(self, sql: str, params: Sequence[Any] | None = None) -> int:
        """Ejecuta un script T-SQL (tipicamente un DELETE parametrizado) y
        devuelve la cantidad de filas afectadas."""
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, tuple(params) if params else ())
                filas = cursor.rowcount
                self._conn.commit()
                return filas if filas is not None and filas >= 0 else 0
            finally:
                cursor.close()
        except Exception as exc:
            self._conn.rollback()
            raise CargaError(f"Fallo la ejecucion del script T-SQL: {exc}") from exc

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(f"TRUNCATE TABLE [{schema}].[{table}]")
                self._conn.commit()
            finally:
                cursor.close()
        except Exception as exc:
            self._conn.rollback()
            raise CargaError(f"Fallo al truncar [{schema}].[{table}]: {exc}") from exc
        logger.info("Tabla [%s].[%s] truncada.", schema, table)

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> int:
        """Inserta un DataFrame por lotes (fast_executemany). Devuelve la
        cantidad de filas insertadas. Cualquier fallo detiene el lote
        completo (no hay disposicion 'IgnoreFailure' aqui: si un lote falla,
        se levanta CargaError)."""
        if df.empty:
            logger.warning("bulk_insert: DataFrame vacio para [%s].[%s], no se inserta nada.", schema, table)
            return 0

        insert_sql = self._insert_sql(table, list(df.columns), schema)

        try:
            cursor = self._conn.cursor()
            try:
                total_insertadas = 0
                for inicio in range(0, len(df), self._batch_size):
                    lote = df.iloc[inicio : inicio + self._batch_size]
                    params = [_fila_a_parametros(fila) for fila in lote.itertuples(index=False, name=None)]
                    self._executemany(cursor, insert_sql, params, table, schema)
                    self._conn.commit()
                    total_insertadas += len(params)
            finally:
                cursor.close()

            logger.info("%s fila(s) insertadas en [%s].[%s].", total_insertadas, schema, table)
            return total_insertadas
        except Exception as exc:
            self._conn.rollback()
            raise CargaError(f"No se pudieron insertar filas en [{schema}].[{table}]: {exc}") from exc

    @staticmethod
    def _executemany(cursor: pyodbc.Cursor, sql: str, params: list[tuple], table: str, schema: str) -> None:
        try:
            cursor.fast_executemany = True
        except Exception:
            pass
        try:
            cursor.executemany(sql, params)
        except pyodbc.Error as exc:
            if "right truncation" not in str(exc).lower():
                raise
            # fast_executemany estima el buffer de cada columna a partir de
            # las primeras filas del lote -- con una columna de longitud muy
            # variable (ej. NVARCHAR(MAX) 'Asunto', un asunto de correo de
            # miles de caracteres junto a otros de unas pocas decenas) puede
            # quedarse corto y truncar. Reintenta el mismo lote sin
            # fast_executemany (mas lento, pero no adivina tamanos de buffer).
            logger.warning(
                "bulk_insert: fast_executemany fallo en [%s].[%s] por una columna de longitud "
                "muy variable, reintentando el lote sin fast_executemany.",
                schema,
                table,
            )
            cursor.fast_executemany = False
            cursor.executemany(sql, params)

    @staticmethod
    def _insert_sql(table: str, columnas: list[str], schema: str) -> str:
        columnas_sql = ", ".join(f"[{c}]" for c in columnas)
        placeholders = ", ".join("?" for _ in columnas)
        return f"INSERT INTO [{schema}].[{table}] ({columnas_sql}) VALUES ({placeholders})"
