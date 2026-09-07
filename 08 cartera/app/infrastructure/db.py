"""Adaptador de infraestructura: fabrica de conexiones SQL Server (pyodbc).

Equivalente a los Connection Managers OLE DB 'PEOPEDESK0328.CL_CARTERA' y
'PEOPEDESK0328.CL_TEMPORALES' del paquete SSIS original. Se crea una
conexion por cada uno (mismo servidor, distinta base de datos), igual que en
el .dtsx.
"""

from __future__ import annotations

import pyodbc

from app.infrastructure.config import DbSettings


def crear_conexion(settings: DbSettings) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{settings.driver}}};"
        f"SERVER={settings.server};"
        f"DATABASE={settings.database};"
        f"UID={settings.user};"
        f"PWD={settings.password};"
        f"Encrypt={settings.encrypt};"
        f"TrustServerCertificate={settings.trust_server_certificate}"
    )
    return pyodbc.connect(conn_str)
