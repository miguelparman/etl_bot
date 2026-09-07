"""Carga masiva hacia SQL Server (equivalente a los OLE DB Destination con
fast load / TABLOCK+CHECK_CONSTRAINTS de los Data Flow Tasks originales)."""
from __future__ import annotations

import polars as pl
import pyodbc

#: tamaño de lote para executemany; ajustar segun ancho de fila / memoria disponible
DEFAULT_BATCH_SIZE = 5_000


def bulk_insert(
    conn: pyodbc.Connection,
    df: pl.DataFrame,
    table_fqn: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Inserta un DataFrame completo en `table_fqn` (p.ej. "[CL_ISN].[dbo].[TBL_X]").

    Usa fast_executemany de pyodbc (conn.cursor().fast_executemany = True),
    equivalente al AccessMode=3 ("carga rapida") + FastLoadKeepNulls=True del
    destino OLE DB original: los valores None se insertan como NULL real, no
    como cadena vacia.
    """
    if df.height == 0:
        return 0

    columns = df.columns
    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(f"[{c}]" for c in columns)
    insert_sql = f"INSERT INTO {table_fqn} ({col_list}) VALUES ({placeholders})"

    cursor = conn.cursor()
    cursor.fast_executemany = True

    rows = df.rows()  # list[tuple], None ya representa NULL
    inserted = 0
    try:
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            cursor.executemany(insert_sql, batch)
            inserted += len(batch)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted
