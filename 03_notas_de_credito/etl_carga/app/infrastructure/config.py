"""Adaptador de infraestructura: arma ETLSettings a partir de variables de
entorno (archivo '.env'), con valores por defecto si no están definidas.

Equivalente a los Connection Managers y a las variables User::Año / User::Mes
del paquete SSIS_CL_NC.dtsx.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from app.domain.models import ColumnasNC, ETLSettings, PeriodoCarga

_DEFAULT_EXCEL_PATH = (
    r"D:\OneDrive - IRISCENE ENGINEERING CORPORATION SLU\Insumos Chile\Informes\NC\DB\NC_.xlsx"
)
_DEFAULT_TABLA_STAGING = "[CL_FACTURACION].[dbo].[TBL_NC_Temp]"
_DEFAULT_TABLA_DESTINO = "[CL_FACTURACION].[dbo].[TBL_NC_DB]"


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(
    base_dir: Path,
    anio: int | None = None,
    mes: int | None = None,
) -> ETLSettings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuración del dominio.

    'anio'/'mes' permiten sobrescribir el período por línea de comandos, igual
    que en SSIS se editaban a mano las variables User::Año / User::Mes antes
    de cada corrida mensual. Si no se pasan, se toman de .env y, en su
    defecto, del mes/año actuales.
    """
    load_dotenv(base_dir / ".env")
    # ANIO/MES ya no se definen en este .env: viven en el .env general del
    # pipeline (carpeta padre), compartido con bot_extraccion. Se carga como
    # respaldo (no pisa lo que ya esté en el entorno, p. ej. inyectado por
    # el orquestador raíz con --anio/--mes).
    load_dotenv(base_dir.parent / ".env")

    hoy = date.today()
    periodo = PeriodoCarga(
        anio=anio if anio is not None else _env_int("ANIO", hoy.year),
        mes=mes if mes is not None else _env_int("MES", hoy.month),
    )

    return ETLSettings(
        periodo=periodo,
        db_driver=os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}"),
        db_server=os.getenv("DB_SERVER", "172.17.0.162"),
        db_database=os.getenv("DB_DATABASE", "CL_FACTURACION"),
        db_uid=os.getenv("DB_UID", ""),
        db_pwd=os.getenv("DB_PWD", ""),
        db_encrypt=os.getenv("DB_ENCRYPT", "no"),
        db_trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes"),
        excel_path=Path(os.getenv("EXCEL_PATH", _DEFAULT_EXCEL_PATH)),
        tabla_staging=os.getenv("TABLA_STAGING", _DEFAULT_TABLA_STAGING),
        tabla_destino=os.getenv("TABLA_DESTINO", _DEFAULT_TABLA_DESTINO),
        columnas=ColumnasNC(),
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "etl_nc.log",
    )
