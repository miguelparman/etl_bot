"""Conexion a SQL Server y ejecucion de scripts .sql (equivalente a los
Connection Managers OLE DB "162.CL_ISN" / "162.CL_CALIDAD" y a la ejecucion
de Execute SQL Tasks del paquete original).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pyodbc
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

from src.config.settings import SQL_DIR, DatabaseSettings

_GO_SPLIT_RE = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)


def build_engine(db: DatabaseSettings) -> Engine:
    """Crea el Engine de SQLAlchemy con fast_executemany habilitado.

    fast_executemany es el equivalente en pyodbc al "fast load" (AccessMode=3,
    FastLoadOptions=TABLOCK,CHECK_CONSTRAINTS) usado por los OLE DB
    Destination del paquete original.
    """
    return create_engine(db.sqlalchemy_url, fast_executemany=True, pool_pre_ping=True)


def build_raw_connection(db: DatabaseSettings) -> pyodbc.Connection:
    """Conexion pyodbc cruda, usada por el loader de carga masiva."""
    conn_str = (
        f"DRIVER={{{db.driver}}};"
        f"SERVER={db.server},{db.port};"
        f"DATABASE={db.database};"
        f"UID={db.user};"
        f"PWD={db.password};"
        f"Encrypt={'yes' if db.encrypt else 'no'};"
        f"TrustServerCertificate={'yes' if db.trust_server_certificate else 'no'};"
    )
    conn = pyodbc.connect(conn_str)
    conn.autocommit = False
    return conn


@contextmanager
def raw_connection(db: DatabaseSettings) -> Iterator[pyodbc.Connection]:
    """Conexion pyodbc de un solo uso (se cierra al salir del ``with``).

    Cada paso de carga masiva abre/cierra la suya: pyodbc.Connection no es
    segura para compartir entre hilos, y las ramas paralelas del pipeline
    (ver src/main.py) corren en threads distintos.
    """
    conn = build_raw_connection(db)
    try:
        yield conn
    finally:
        conn.close()


def load_sql(filename: str) -> str:
    """Lee un archivo .sql desde la carpeta sql/ del proyecto."""
    path = SQL_DIR / filename
    return path.read_text(encoding="utf-8")


def split_batches(sql_text: str) -> list[str]:
    """Divide un script en lotes separados por 'GO', igual que hace SSMS/SSIS.

    SQLAlchemy/pyodbc no entienden 'GO' (es una convencion de cliente, no
    T-SQL real), por lo que scripts multi-lote como
    02_rebuild_tablas_auxiliares.sql deben partirse antes de ejecutarse.
    """
    batches = [b.strip() for b in _GO_SPLIT_RE.split(sql_text)]
    return [b for b in batches if b]


def execute_script(conn: Connection, filename: str, params: dict[str, Any] | None = None) -> None:
    """Ejecuta un archivo .sql completo, respetando separadores GO si existen."""
    sql_text = load_sql(filename)
    for batch in split_batches(sql_text):
        conn.execute(text(batch), params or {})


def fetch_all(conn: Connection, filename: str, params: dict[str, Any] | None = None):
    sql_text = load_sql(filename)
    return conn.execute(text(sql_text), params or {})
