"""Factoria del engine de SQLAlchemy para SQL Server (via pyodbc).

Sustituye al Connection Manager OLE DB '162.CL_USUARIOS' (Provider
MSOLEDBSQL.1) de los paquetes SSIS originales por el driver ODBC estandar.
"""

from __future__ import annotations

import urllib.parse

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from etl_chile.config.settings import DatabaseSettings


def create_sqlserver_engine(settings: DatabaseSettings) -> Engine:
    odbc_connection_string = (
        f"DRIVER={{{settings.driver}}};"
        f"SERVER={settings.server};"
        f"DATABASE={settings.database};"
        f"UID={settings.user};"
        f"PWD={settings.password};"
        f"Encrypt={settings.encrypt};"
        f"TrustServerCertificate={settings.trust_server_certificate};"
    )
    quoted = urllib.parse.quote_plus(odbc_connection_string)
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quoted}",
        fast_executemany=True,
    )
