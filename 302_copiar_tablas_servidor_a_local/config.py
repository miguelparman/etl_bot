"""Arma la configuracion a partir de variables de entorno (archivo '.env'),
con valores por defecto no sensibles si no estan definidas. Ninguna
credencial vive en el codigo ni en este repositorio.

Dos conexiones: 'origen' (servidor 172.17.0.162, autenticacion SQL Server) y
'destino' (servidor local, por defecto con autenticacion Windows integrada).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from exceptions import CopiaTablaError


@dataclass(frozen=True)
class DbSettings:
    server: str
    database: str
    user: str | None
    password: str | None
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "no"
    trust_server_certificate: str = "yes"


@dataclass(frozen=True)
class Settings:
    db_origen: DbSettings
    db_destino: DbSettings
    batch_size: int = 5000
    log_file: Path = Path("copiar_tablas.log")


def _require_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise CopiaTablaError(f"La variable de entorno '{nombre}' es obligatoria. Ver .env.example.")
    return valor


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path) -> Settings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuracion."""
    load_dotenv(base_dir / ".env")

    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt = os.getenv("DB_ENCRYPT", "no")
    trust_cert = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")

    db_origen = DbSettings(
        server=_require_env("ORIGEN_DB_SERVER"),
        database=os.getenv("ORIGEN_DB_NAME", "CL_CARTERA"),
        user=_require_env("ORIGEN_DB_USER"),
        password=_require_env("ORIGEN_DB_PASSWORD"),
        driver=driver,
        encrypt=encrypt,
        trust_server_certificate=trust_cert,
    )

    db_destino = DbSettings(
        server=os.getenv("DESTINO_DB_SERVER", "localhost"),
        database=os.getenv("DESTINO_DB_NAME", "CL_CARTERA"),
        user=os.getenv("DESTINO_DB_USER") or None,
        password=os.getenv("DESTINO_DB_PASSWORD") or None,
        driver=driver,
        encrypt=encrypt,
        trust_server_certificate=trust_cert,
    )

    return Settings(
        db_origen=db_origen,
        db_destino=db_destino,
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "copiar_tablas.log",
    )
