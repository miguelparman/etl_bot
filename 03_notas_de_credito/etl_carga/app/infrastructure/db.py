"""Adaptador de infraestructura: fábrica de conexiones SQL Server (pyodbc).

Equivalente al Connection Manager OLE DB '162.CL_FACTURACION' del paquete SSIS.
"""

from __future__ import annotations

import pyodbc

from app.domain.models import ETLSettings


def crear_conexion(settings: ETLSettings) -> pyodbc.Connection:
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
