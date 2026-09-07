"""Adaptador de infraestructura: tabla final TBL_NC_DB.

Implementa el puerto DestinoRepository (app/application/ports.py). Cubre lo
que en el paquete SSIS eran la tarea 'DELETE NC', el Data Flow 'CARGA NC'
(destino OLE DB con FastLoad) y la tarea 'UPDATE' de homologación de
ejecutivos.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import pyodbc

from app.domain.exceptions import CargaDestinoError
from app.domain.models import ColumnasNC, PeriodoCarga

logger = logging.getLogger("etl_nc")

_SQL_UPDATE_EJECUTIVO = (Path(__file__).parent / "sql" / "update_ejecutivo.sql").read_text(encoding="utf-8")


class SqlServerDestinoRepository:
    """Implementa el puerto DestinoRepository (app/application/ports.py)."""

    def __init__(self, conn: pyodbc.Connection, tabla: str, columnas: ColumnasNC, batch_size: int) -> None:
        self._conn = conn
        self._tabla = tabla
        self._columnas = columnas
        self._batch_size = batch_size

    def eliminar_periodo(self, periodo: PeriodoCarga) -> int:
        sql = f"DELETE {self._tabla} WHERE YEAR(FECHA_NC) = ? AND MONTH(FECHA_NC) = ?"
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, (periodo.anio, periodo.mes))
                filas = cursor.rowcount
                self._conn.commit()
            finally:
                cursor.close()
            logger.info("DELETE NC: %s filas eliminadas de %s.", filas, self._tabla)
            return filas
        except Exception as exc:
            self._conn.rollback()
            raise CargaDestinoError(f"Falló DELETE NC sobre {self._tabla}: {exc}") from exc

    def cargar_desde(self, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0

        columnas_sql = ", ".join(f"[{c}]" for c in self._columnas.nombres)
        placeholders = ", ".join("?" for _ in self._columnas.nombres)
        insert_sql = f"INSERT INTO {self._tabla} ({columnas_sql}) VALUES ({placeholders})"

        try:
            cursor = self._conn.cursor()
            try:
                try:
                    cursor.fast_executemany = True
                except Exception:
                    pass

                total_insertadas = 0
                for inicio in range(0, len(df), self._batch_size):
                    lote = df.slice(inicio, self._batch_size)
                    params = [
                        tuple(fila[col] for col in self._columnas.nombres)
                        for fila in lote.iter_rows(named=True)
                    ]
                    cursor.executemany(insert_sql, params)
                    self._conn.commit()
                    total_insertadas += len(params)
            finally:
                cursor.close()

            logger.info("CARGA NC: %s filas cargadas en %s.", total_insertadas, self._tabla)
            return total_insertadas
        except Exception as exc:
            self._conn.rollback()
            raise CargaDestinoError(f"Falló CARGA NC sobre {self._tabla}: {exc}") from exc

    def normalizar_ejecutivos(self, periodo: PeriodoCarga) -> int:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(_SQL_UPDATE_EJECUTIVO, (periodo.anio, periodo.mes))
                filas = cursor.rowcount
                self._conn.commit()
            finally:
                cursor.close()
            logger.info("UPDATE: %s filas de %s con EJECUTIVO homologado.", filas, self._tabla)
            return filas
        except Exception as exc:
            self._conn.rollback()
            raise CargaDestinoError(f"Falló la homologación de EJECUTIVO sobre {self._tabla}: {exc}") from exc
