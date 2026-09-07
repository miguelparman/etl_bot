"""Configuracion de la aplicacion, cargada desde variables de entorno / .env.

Sustituye a los Connection Managers y rutas hardcodeadas de los paquetes SSIS
originales (CROSS 0101 SSIS_CL_Senalizaciones.dtsx y CROSS 0102 SSIS_CL_Ventas.dtsx).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from etl_chile.domain.exceptions import ConfigurationError


@dataclass(frozen=True)
class DatabaseSettings:
    """Equivalente al Connection Manager OLE DB '162.CL_USUARIOS'."""

    server: str
    database: str
    user: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "no"
    trust_server_certificate: str = "yes"


@dataclass(frozen=True)
class FilePathsSettings:
    """Rutas de archivos, equivalentes a los Connection Managers FLATFILE/EXCEL."""

    senalizaciones_csv: Path
    base_carta_meta_xlsx: Path
    funnel_ventas_v2_xlsx: Path


@dataclass(frozen=True)
class GoogleSheetSettings:
    """Equivalente al Execute Process Task que invocaba Ch_Senhalizaciones.py."""

    csv_export_url: str
    num_columns: int = 39


@dataclass(frozen=True)
class PackageParameters:
    """Espeja, uno a uno, la declaracion de Parameters/Variables de
    CROSS 0102 SSIS_CL_Ventas.dtsx (seccion 3 de la especificacion del
    paquete). Se conserva la declaracion completa por fidelidad con el
    proyecto original, aunque `periodo` y `fec` no se usan en ningun SQL ni
    expresion del .dtsx (quedan documentados como vestigiales, igual que
    alli).

    - `periodo`: Project Parameter `Periodo` (DT_I4). Valor de diseno
      original: 202505. No referenciado en ninguna parte del paquete.
    - `fecha`: Package Variable `User::Fecha` (DT_DATE). Es el UNICO de los
      tres realmente usado en tiempo de ejecucion: cutoff en 2 Execute SQL
      Task. En el .dtsx original no se calculaba dentro del paquete: lo
      inyectaba el proceso/scheduler que lo invocaba (`dtexec /Set
      \\Package.Variables[User::Fecha].Value=...`). Aqui se declara en
      `.env` (VAR_FECHA) y puede sobreescribirse puntualmente con `--fecha`
      en la CLI.
    - `fec`: Package Variable `User::Fec` (DT_I4). Valor de diseno original:
      0. No referenciado en ninguna parte del paquete.
    """

    periodo: int = 202505
    fecha: date | None = None
    fec: int = 0


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    paths: FilePathsSettings
    google_sheet: GoogleSheetSettings
    parameters: PackageParameters
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(dotenv_path=env_file)

        db_password = os.getenv("DB_PASSWORD", "")
        if not db_password:
            raise ConfigurationError(
                "DB_PASSWORD no esta definida. Configure un archivo .env "
                "(ver .env.example) o exporte la variable de entorno."
            )

        return cls(
            database=DatabaseSettings(
                server=_require_env("DB_SERVER"),
                database=os.getenv("DB_NAME", "CL_USUARIOS"),
                user=_require_env("DB_USER"),
                password=db_password,
                driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
                encrypt=os.getenv("DB_ENCRYPT", "no"),
                trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes"),
            ),
            paths=FilePathsSettings(
                senalizaciones_csv=Path(_require_env("PATH_SENALIZACIONES_CSV")),
                base_carta_meta_xlsx=Path(_require_env("PATH_BASE_CARTA_META_XLSX")),
                funnel_ventas_v2_xlsx=Path(_require_env("PATH_FUNNEL_VENTAS_V2_XLSX")),
            ),
            google_sheet=GoogleSheetSettings(
                csv_export_url=_require_env("GOOGLE_SHEET_SENALIZACIONES_CSV_URL"),
                num_columns=int(os.getenv("GOOGLE_SHEET_SENALIZACIONES_NUM_COLUMNS", "39")),
            ),
            parameters=PackageParameters(
                periodo=int(os.getenv("PARAM_PERIODO", "202505")),
                fecha=_parse_optional_date(os.getenv("VAR_FECHA")),
                fec=int(os.getenv("VAR_FEC", "0")),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(
            f"La variable de entorno '{name}' es obligatoria. Ver .env.example."
        )
    return value


def _parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigurationError(
            f"VAR_FECHA='{value}' invalida, formato esperado YYYY-MM-DD."
        ) from exc
