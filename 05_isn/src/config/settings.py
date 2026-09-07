"""Configuracion centralizada del ETL, cargada desde variables de entorno.

Equivalente a: Connection Managers + Variables de paquete del .dtsx original.
Ningun valor sensible vive hardcodeado aqui: todo se resuelve via .env
(ver .env.example) siguiendo la regla de no credenciales en el codigo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_ROOT / "sql"

load_dotenv(PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria '{name}'. "
            f"Revisa tu archivo .env (ver .env.example)."
        )
    return value


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()  # noqa: DTZ007 - solo fecha, sin hora/zona


@dataclass(frozen=True)
class DatabaseSettings:
    server: str
    port: int
    database: str
    user: str
    password: str
    driver: str
    encrypt: bool
    trust_server_certificate: bool

    @property
    def sqlalchemy_url(self) -> str:
        # pyodbc + fast_executemany se habilita al crear el Engine (ver database/connection.py)
        from urllib.parse import quote_plus

        odbc_str = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"Encrypt={'yes' if self.encrypt else 'no'};"
            f"TrustServerCertificate={'yes' if self.trust_server_certificate else 'no'};"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"


@dataclass(frozen=True)
class FilePathSettings:
    automatizado_dir: Path
    aux_cliente_csv: Path
    aux_contacto_csv: Path

    @property
    def isn_source_csv(self) -> Path:
        """Equivalente al Connection Manager de archivo plano 'CSV' (isn.csv)."""
        return self.automatizado_dir / "Source" / "isn.csv"

    def dated_archive_csv(self, run_date: date) -> Path:
        """Equivalente a la expresion de la variable User::New_name_file."""
        return self.automatizado_dir / f"PROSPECTOS_EMPRESA_{run_date:%Y%m%d}.csv"


@dataclass(frozen=True)
class Settings:
    db: DatabaseSettings
    paths: FilePathSettings
    fecha_inicio: date | None
    fecha_fin: date | None
    log_level: str
    log_dir: Path


def load_settings() -> Settings:
    db = DatabaseSettings(
        server=_require("DB_SERVER"),
        port=int(os.getenv("DB_PORT", "1433")),
        database=os.getenv("DB_DATABASE", "CL_ISN"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        encrypt=os.getenv("DB_ENCRYPT", "yes").lower() == "yes",
        trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "no").lower() == "yes",
    )
    paths = FilePathSettings(
        automatizado_dir=Path(_require("ISN_AUTOMATIZADO_DIR")),
        aux_cliente_csv=Path(_require("ISN_AUX_CLIENTE_CSV")),
        aux_contacto_csv=Path(_require("ISN_AUX_CONTACTO_CSV")),
    )
    return Settings(
        db=db,
        paths=paths,
        fecha_inicio=_parse_date(os.getenv("FECHA_INICIO")),
        fecha_fin=_parse_date(os.getenv("FECHA_FIN")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
    )


def default_fecha_range() -> tuple[date, date]:
    """Default cuando no se especifica ventana de fechas.

    El .dtsx original tenia Fecha_inicio/Fecha_fin como valores FIJOS grabados
    en el diseñador (no una expresion con GETDATE()), lo que en la practica
    significa que alguien los actualizaba a mano antes de cada corrida o via
    un paso externo no presente en este archivo. Como no hay una regla
    explicita que reconstruir, se adopta "ayer" (fecha_inicio = fecha_fin =
    ayer) como default explicito y documentado, sobreescribible por
    --fecha-inicio/--fecha-fin o por las variables de entorno FECHA_INICIO/
    FECHA_FIN. Confirmar con negocio si el default correcto es otro.
    """
    yesterday = date.today() - timedelta(days=1)  # noqa: DTZ011 - fecha local, igual que GETDATE() en el original
    return yesterday, yesterday
