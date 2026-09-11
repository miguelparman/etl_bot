"""Adaptador de infraestructura: tabla de staging TBL_NC_Temp.

Implementa el puerto StagingRepository (app/application/ports.py). Cubre lo
que en el paquete SSIS eran las tareas 'DELETE' y 'DELETE 2', más el truncado
e inserción que hacía ETL_NC_polars.py.
"""

from __future__ import annotations

import logging

import polars as pl
import pyodbc

from app.domain.exceptions import StagingError
from app.domain.models import ColumnasNC, PeriodoCarga

logger = logging.getLogger("etl_nc")

# Filas de "Total"/"Filtros aplicados" que Power BI agrega al pie del export
# y que la tarea 'DELETE 2' del paquete original eliminaba de TBL_NC_Temp.
_VALORES_RUT_INVALIDOS = ("Total", "Filtros aplicad")


class SqlServerStagingRepository:
    """Implementa el puerto StagingRepository (app/application/ports.py)."""

    def __init__(self, conn: pyodbc.Connection, tabla: str, columnas: ColumnasNC, batch_size: int) -> None:
        self._conn = conn
        self._tabla = tabla
        self._columnas = columnas
        self._batch_size = batch_size

    def truncar(self) -> None:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(f"TRUNCATE TABLE {self._tabla}")
                self._conn.commit()
            finally:
                cursor.close()
            logger.info("Tabla %s truncada.", self._tabla)
        except Exception as exc:
            self._conn.rollback()
            raise StagingError(f"No se pudo truncar {self._tabla}: {exc}") from exc

    def insertar(self, df: pl.DataFrame) -> int:
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

            logger.info("%s filas insertadas en %s.", total_insertadas, self._tabla)
            return total_insertadas
        except Exception as exc:
            self._conn.rollback()
            raise StagingError(f"No se pudieron insertar filas en {self._tabla}: {exc}") from exc

    def eliminar_fuera_de_periodo(self, periodo: PeriodoCarga) -> int:
        # Réplica literal de la tarea 'DELETE': AND (no OR) entre año y mes,
        # tal como estaba definido en el paquete SSIS original.
        sql = f"DELETE {self._tabla} WHERE YEAR(FECHA_NC) <> ? AND MONTH(FECHA_NC) <> ?"
        return self._ejecutar_delete(sql, (periodo.anio, periodo.mes), "eliminar_fuera_de_periodo")

    def eliminar_filas_invalidas(self) -> int:
        # Réplica de la tarea 'DELETE 2' (tres DELETE separados en el paquete
        # original), combinada en una sola sentencia equivalente.
        sql = (
            f"DELETE {self._tabla} "
            "WHERE RUT IS NULL OR RUT = ? OR RUT = ?"
        )
        return self._ejecutar_delete(sql, _VALORES_RUT_INVALIDOS, "eliminar_filas_invalidas")

    def leer_todo(self) -> pl.DataFrame:
        columnas_sql = ", ".join(f"[{c}]" for c in self._columnas.nombres)
        try:
            return pl.read_database(
                query=f"SELECT {columnas_sql} FROM {self._tabla}",
                connection=self._conn,
            )
        except Exception as exc:
            raise StagingError(f"No se pudo leer {self._tabla}: {exc}") from exc

    def _ejecutar_delete(self, sql: str, params: tuple, nombre_operacion: str) -> int:
        try:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, params)
                filas = cursor.rowcount
                self._conn.commit()
            finally:
                cursor.close()
            logger.info("%s: %s filas eliminadas de %s.", nombre_operacion, filas, self._tabla)
            return filas
        except Exception as exc:
            self._conn.rollback()
            raise StagingError(f"Falló {nombre_operacion} sobre {self._tabla}: {exc}") from exc
