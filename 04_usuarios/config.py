"""Arma la configuracion a partir de variables de entorno (archivo '.env').
Ninguna credencial vive en el codigo ni en este repositorio.

Equivalente a los 2 Connection Managers OLE DB (CL_USUARIOS y Externos_Frac)
y a la variable de paquete User::Periodo / User::Periodo01, presentes por
igual en los 5 .dtsx originales.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from exceptions import UsuariosError
from models import Periodo


@dataclass(frozen=True)
class DbSettings:
    """Equivalente a un Connection Manager OLE DB (Provider MSOLEDBSQL.1).

    'user'/'password' quedan en None para un Connection Manager con
    autenticacion de Windows integrada (SSPI) -- ver db.crear_conexion."""

    server: str
    database: str
    driver: str = "ODBC Driver 18 for SQL Server"
    user: str | None = None
    password: str | None = None
    encrypt: str = "no"
    trust_server_certificate: str = "yes"


@dataclass(frozen=True)
class Settings:
    db_cl_usuarios: DbSettings  # Connection Manager 'LocalHost.CL_USUARIOS' / '162.CL_USUARIOS' (auth SQL)
    db_externos_frac: DbSettings  # Connection Manager '223.Externos_Frac...' (auth Windows integrada)
    periodo: Periodo | None  # User::Periodo / User::Periodo01
    batch_size: int = 5000
    log_file: Path = Path("usuarios.log")


def _require_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise UsuariosError(f"La variable de entorno '{nombre}' es obligatoria. Ver .env.example.")
    return valor


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path, periodo: str | None = None) -> Settings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuracion.

    'periodo' permite sobrescribir por linea de comandos el valor de
    PERIODO de '.env' -- igual que en SSIS se editaba a mano la expresion de
    la variable User::Periodo / User::Periodo01 antes de cada corrida.
    """
    load_dotenv(base_dir / ".env")

    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt = os.getenv("DB_ENCRYPT", "no")
    trust_cert = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")

    db_cl_usuarios = DbSettings(
        server=_require_env("CL_USUARIOS_DB_SERVER"),
        database=os.getenv("CL_USUARIOS_DB_NAME", "CL_USUARIOS"),
        driver=driver,
        user=_require_env("CL_USUARIOS_DB_USER"),
        password=_require_env("CL_USUARIOS_DB_PASSWORD"),
        encrypt=encrypt,
        trust_server_certificate=trust_cert,
    )
    db_externos_frac = DbSettings(
        server=_require_env("EXTERNOS_FRAC_DB_SERVER"),
        database=os.getenv("EXTERNOS_FRAC_DB_NAME", "Externos_Frac"),
        driver=driver,
        user=None,
        password=None,
        encrypt=encrypt,
        trust_server_certificate=trust_cert,
    )

    valor_periodo = periodo if periodo is not None else os.getenv("PERIODO")

    return Settings(
        db_cl_usuarios=db_cl_usuarios,
        db_externos_frac=db_externos_frac,
        periodo=Periodo(valor_periodo) if valor_periodo else None,
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "usuarios.log",
    )
