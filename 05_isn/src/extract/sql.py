"""Lectura de resultados SQL como DataFrame Polars (equivalente a los OLE DB
Source en modo tabla/SQL command de los Data Flow Tasks)."""
from __future__ import annotations

from typing import Any

import polars as pl
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.database.connection import load_sql


def read_query(conn: Connection, filename: str, params: dict[str, Any] | None = None) -> pl.DataFrame:
    sql_text = load_sql(filename)
    result = conn.execute(text(sql_text), params or {})
    rows = result.fetchall()
    columns = list(result.keys())
    return pl.DataFrame(rows, schema=columns, orient="row")
