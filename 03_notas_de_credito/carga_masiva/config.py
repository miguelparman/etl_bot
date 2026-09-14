"""Configuración de la carga masiva: variables de entorno ('.env') -> Settings.

Módulo autocontenido -- igual que bot_extraccion/etl_carga, trae su propio
'.env' y no importa nada de esos otros módulos del pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DEFAULT_EXCEL_PATH = (
    r"D:\OneDrive - IRISCENE ENGINEERING CORPORATION SLU\Insumos Chile\Informes\NC\DB\NC_.xlsx"
)
_DEFAULT_TABLA_DESTINO = "[CL_FACTURACION].[dbo].[TBL_NC_DB]"

# Orden y nombres de columnas del Excel de origen y de la tabla destino.
COLUMNAS: tuple[str, ...] = (
    "RUT",
    "RAZON_SOCIAL",
    "FOLIO_NC",
    "FECHA_NC",
    "NETO_NC",
    "IVA_NC",
    "TOTAL_NC",
    "EJECUTIVO",
)


@dataclass(frozen=True)
class Settings:
    db_driver: str
    db_server: str
    db_database: str
    db_uid: str
    db_pwd: str
    db_encrypt: str
    db_trust_server_certificate: str

    excel_path: Path
    tabla_destino: str
    batch_size: int

    log_file: Path


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path) -> Settings:
    """Carga '.env' (junto a main.py) y arma la configuración."""
    load_dotenv(base_dir / ".env")

    return Settings(
        db_driver=os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}"),
        db_server=os.getenv("DB_SERVER", "172.17.0.162"),
        db_database=os.getenv("DB_DATABASE", "CL_FACTURACION"),
        db_uid=os.getenv("DB_UID", ""),
        db_pwd=os.getenv("DB_PWD", ""),
        db_encrypt=os.getenv("DB_ENCRYPT", "no"),
        db_trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes"),
        excel_path=Path(os.getenv("EXCEL_PATH", _DEFAULT_EXCEL_PATH)),
        tabla_destino=os.getenv("TABLA_DESTINO", _DEFAULT_TABLA_DESTINO),
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "carga_masiva.log",
    )
