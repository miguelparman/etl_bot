"""
Manejo de conexiones y ejecución SQL contra SQL Server.

Reemplaza los tres Connection Manager OLEDB de los paquetes originales:
"162.CL_ANALISIS.mparedes" (SSIS_CL_ISN_Contactos), "162.CL_ISN" y
"162.CL_CALIDAD" (SSIS_CL_ISN). Los tres viven en el mismo servidor, así que
se resuelven como tres engines de SQLAlchemy que solo difieren en la base.

`run_sql_file` divide el script en batches separados por una línea que
contiene únicamente "GO" (como hace SSMS/sqlcmd), porque el driver ODBC no
entiende "GO" como comando: varios Execute SQL Task del .dtsx original traen
más de un batch en un mismo SqlStatementSource (p. ej. "TBLS AUXILIARES",
con 4 bloques DROP+SELECT INTO separados por GO). Cada batch se ejecuta con
autocommit, igual que hace SSIS al correr un Execute SQL Task con varios GO.
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from config import settings

logger = logging.getLogger(__name__)

_GO_LINE = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)

_engines: dict[str, Engine] = {}


def get_engine(database: str) -> Engine:
    """Devuelve (y cachea) el engine SQLAlchemy para una base dada del mismo
    servidor. Se usa para los Execute SQL Task (run_sql/run_sql_file) y para
    TRUNCATE -- ninguno hace binding de arrays de filas, así que
    fast_executemany no aplica acá (la carga masiva real usa pyodbc directo,
    ver get_raw_pyodbc_connection / common/sql_loader.py::load_dataframe).
    """
    if database not in _engines:
        _engines[database] = create_engine(settings.sqlalchemy_url(database), fast_executemany=False)
    return _engines[database]


@contextmanager
def get_raw_pyodbc_connection(database: str) -> Iterator[pyodbc.Connection]:
    """Conexión pyodbc directa (sin SQLAlchemy), para cargas masivas
    (common/sql_loader.py::load_dataframe).

    Se probó primero con pandas.to_sql (SQLAlchemy 2.x + mssql+pyodbc):
    para una tabla ancha arma un único INSERT multi-fila
    ("insertmanyvalues") envuelto en una sola transacción por llamada, y con
    fast_executemany=True el driver reventó a mitad de carga con "String
    data, right truncation" -- resultó ser el mismo problema de fondo que
    reventó después con el mensaje nativo de SQL Server ("Los datos... se
    truncan"): un valor real de MÓVIL/TELÉFONO más largo que el ancho
    declarado de la columna (ver contactos/columns.py::COLUMNAS_TRUNCAR_SILENCIOSO).
    Con esos anchos ya controlados en transformer.py/validator.py ANTES de
    llegar acá, fast_executemany=True vuelve a ser seguro y es 10-50x más
    rápido -- confirmado en producción: 402 088 filas en <1 minuto (vs. los
    ~5 minutos del FastLoad original), donde antes de este fix tardaba
    9 minutos y terminaba revirtiendo las 402 088 filas.

    Se usa pyodbc directo (no pandas.to_sql) para poder fijar
    `cursor.fast_executemany` explícitamente y controlar el tamaño de lote y
    el punto de commit uno a uno (ver load_dataframe).
    """
    conn = pyodbc.connect(settings._odbc_string(database), autocommit=False)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_connection(database: str) -> Iterator[Connection]:
    engine = get_engine(database)
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def split_batches(sql: str) -> list[str]:
    """Divide un script en batches separados por una línea que es solo 'GO'."""
    batches = [b.strip() for b in _GO_LINE.split(sql)]
    return [b for b in batches if b]


def run_sql(database: str, sql: str, params: dict | None = None) -> None:
    """Ejecuta un script (con o sin 'GO') dentro de una única conexión/transacción."""
    batches = split_batches(sql)
    with get_connection(database) as conn:
        for batch in batches:
            logger.info("Ejecutando batch SQL en %s (%d caracteres)", database, len(batch))
            conn.execute(text(batch), params or {})


def run_sql_file(database: str, path: str | Path, params: dict | None = None) -> None:
    sql = Path(path).read_text(encoding="utf-8")
    logger.info("Ejecutando %s contra %s con params=%s", path, database, params)
    run_sql(database, sql, params)
