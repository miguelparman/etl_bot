"""Conexión a SQL Server y truncado de la tabla destino."""

from __future__ import annotations

import logging

import pyodbc

from config import Settings

logger = logging.getLogger("carga_masiva")


def crear_conexion(settings: Settings) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={settings.db_driver};"
        f"SERVER={settings.db_server};"
        f"DATABASE={settings.db_database};"
        f"UID={settings.db_uid};"
        f"PWD={settings.db_pwd};"
        f"Encrypt={settings.db_encrypt};"
        f"TrustServerCertificate={settings.db_trust_server_certificate}"
    )
    return pyodbc.connect(conn_str)


def truncar_tabla(conn: pyodbc.Connection, tabla: str) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(f"TRUNCATE TABLE {tabla}")
        conn.commit()
        logger.info("Tabla %s truncada.", tabla)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
