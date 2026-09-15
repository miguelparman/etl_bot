"""Arma la configuracion a partir de variables de entorno (archivo '.env').
Ninguna credencial vive en el codigo ni en este repositorio.

Equivalente al Connection Manager OLE DB 'CL_PLANTA' (destino), al App
Registration de Microsoft Graph que reemplaza al Connection Manager
'srv_chile' (origen, Externos_Frac), y a la variable de paquete
User::Periodo de SSIS_Chile_parque.dtsx.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from exceptions import ParqueError


@dataclass(frozen=True)
class DbSettings:
    """Equivalente al Connection Manager OLE DB 'CL_PLANTA' (Provider MSOLEDBSQL.1)."""

    server: str
    database: str
    user: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "no"
    trust_server_certificate: str = "yes"


@dataclass(frozen=True)
class SharePointSettings:
    """Reemplaza al Connection Manager OLE DB 'srv_chile' (Externos_Frac):
    App Registration de Microsoft Graph con permiso Sites.Selected sobre el
    sitio ReportingFractalia."""

    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    drive_name: str
    folder_path: str
    timeout_ms: int = 120000


@dataclass(frozen=True)
class Settings:
    db: DbSettings
    sharepoint: SharePointSettings
    periodo: str | None  # User::Periodo
    batch_size: int = 5000
    log_file: Path = Path("parque.log")


def _require_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise ParqueError(f"La variable de entorno '{nombre}' es obligatoria. Ver .env.example.")
    return valor


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path, periodo: str | None = None) -> Settings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuracion.

    'periodo' permite sobrescribir por linea de comandos el valor de
    VAR_PERIODO de '.env' -- igual que en SSIS se editaba a mano la
    expresion de la variable User::Periodo antes de cada corrida.
    """
    load_dotenv(base_dir / ".env")

    db = DbSettings(
        server=_require_env("DB_SERVER"),
        database=os.getenv("DB_NAME", "CL_PLANTA"),
        user=_require_env("DB_USER"),
        password=_require_env("DB_PASSWORD"),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        encrypt=os.getenv("DB_ENCRYPT", "no"),
        trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes"),
    )

    sharepoint = SharePointSettings(
        tenant_id=_require_env("TENANT_ID"),
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
        hostname=os.getenv("SHAREPOINT_HOSTNAME", "fractaliagroup.sharepoint.com"),
        site_path=_require_env("SHAREPOINT_SITE_PATH"),
        drive_name=_require_env("SHAREPOINT_DRIVE_NAME"),
        folder_path=_require_env("SHAREPOINT_FOLDER_PATH"),
        timeout_ms=_env_int("GRAPH_TIMEOUT", 120000),
    )

    valor_periodo = periodo if periodo is not None else os.getenv("VAR_PERIODO")
    valor_periodo = valor_periodo.strip() if valor_periodo else None

    return Settings(
        db=db,
        sharepoint=sharepoint,
        periodo=valor_periodo,
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "parque.log",
    )
