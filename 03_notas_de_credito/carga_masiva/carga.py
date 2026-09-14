"""Inserción masiva del DataFrame extraído hacia la tabla destino."""

from __future__ import annotations

import logging

import polars as pl
import pyodbc

from config import COLUMNAS

logger = logging.getLogger("carga_masiva")


def cargar_tabla(conn: pyodbc.Connection, df: pl.DataFrame, tabla: str, batch_size: int) -> int:
    if df.is_empty():
        return 0

    columnas_sql = ", ".join(f"[{c}]" for c in COLUMNAS)
    placeholders = ", ".join("?" for _ in COLUMNAS)
    insert_sql = f"INSERT INTO {tabla} ({columnas_sql}) VALUES ({placeholders})"

    cursor = conn.cursor()
    try:
        try:
            cursor.fast_executemany = True
        except Exception:
            pass

        total_insertadas = 0
        for inicio in range(0, len(df), batch_size):
            lote = df.slice(inicio, batch_size)
            params = [tuple(fila[col] for col in COLUMNAS) for fila in lote.iter_rows(named=True)]
            cursor.executemany(insert_sql, params)
            conn.commit()
            total_insertadas += len(params)
            logger.info("Lote cargado: %s filas (acumulado %s).", len(params), total_insertadas)

        return total_insertadas
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
