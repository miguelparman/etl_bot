"""Adaptador de infraestructura: implementa el puerto DatabaseGateway
(app/application/ports.py) sobre una conexion pyodbc a SQL Server.

Una instancia de esta clase equivale a un Connection Manager OLE DB del
paquete original: el pipeline usa dos (una para CL_CARTERA, otra para
CL_TEMPORALES), cada una con su propia conexion.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

import pandas as pd
import pyodbc

from app.domain.exceptions import CargaError

logger = logging.getLogger("cartera")


class SqlServerGateway:
    """Implementa el puerto DatabaseGateway (app/application/ports.py)."""

    def __init__(self, conn: pyodbc.Connection, batch_size: int = 5000) -> None:
        self._conn = conn
        self._batch_size = batch_size

    def execute_script(self, sql: str, params: Sequence[Any] | None = None) -> None:
        try:
            cursor = self._conn.cursor()
            try:
                if params:
                    cursor.execute(sql, tuple(params))
                else:
                    cursor.execute(sql)
                self._conn.commit()
            finally:
                cursor.close()
        except Exception as exc:
            self._conn.rollback()
            raise CargaError(f"Fallo la ejecucion del script T-SQL: {exc}") from exc

    def fetch_scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, tuple(params) if params else ())
                fila = cursor.fetchone()
                return fila[0] if fila is not None else None
            finally:
                cursor.close()
        except Exception as exc:
            raise CargaError(f"Fallo la consulta escalar: {exc}") from exc

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        self.execute_script(f"TRUNCATE TABLE [{schema}].[{table}]")
        logger.info("Tabla [%s].[%s] truncada.", schema, table)

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> int:
        if df.empty:
            logger.warning("bulk_insert: DataFrame vacio para [%s].[%s], no se inserta nada", schema, table)
            return 0

        columnas = list(df.columns)
        columnas_sql = ", ".join(f"[{c}]" for c in columnas)
        placeholders = ", ".join("?" for _ in columnas)
        insert_sql = f"INSERT INTO [{schema}].[{table}] ({columnas_sql}) VALUES ({placeholders})"

        try:
            cursor = self._conn.cursor()
            try:
                try:
                    cursor.fast_executemany = True
                except Exception:
                    pass

                total_insertadas = 0
                for inicio in range(0, len(df), self._batch_size):
                    lote = df.iloc[inicio : inicio + self._batch_size]
                    params = [tuple(fila) for fila in lote.itertuples(index=False, name=None)]
                    cursor.executemany(insert_sql, params)
                    self._conn.commit()
                    total_insertadas += len(params)
            finally:
                cursor.close()

            logger.info("%s filas insertadas en [%s].[%s].", total_insertadas, schema, table)
            return total_insertadas
        except Exception as exc:
            self._conn.rollback()
            raise CargaError(f"No se pudieron insertar filas en [{schema}].[{table}]: {exc}") from exc

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM [{schema}].[{table}]")
                columnas = [col[0] for col in cursor.description]
                filas = cursor.fetchall()
                return pd.DataFrame.from_records(filas, columns=columnas)
            finally:
                cursor.close()
        except Exception as exc:
            raise CargaError(f"No se pudo leer [{schema}].[{table}]: {exc}") from exc
