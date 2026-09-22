"""Arma la configuracion a partir de variables de entorno ('.env'). Ninguna
credencial vive en el codigo ni en este repositorio.

'BPO' (origen, carpeta 'Control Correos Chile') y 'ReportingFractalia'
(destino, carpeta '14 CORREOS' dentro de 'BPOCHIPE') son tenants de
Microsoft Entra DISTINTOS: cada uno tiene su propio App Registration con
permiso Sites.Selected sobre su site correspondiente -- mismo patron ya
usado en 02_ventas/config.py (SharePointSettings vs SharePointOrigenSettings)
para copiar 'FUNNEL VENTAS V2.xlsx' entre los mismos dos tenants.

DbSettings/cargar_configuracion_db() son para SQL Server ('CL_MOVIL',
172.17.0.162), destino de cargar_correos.py."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from exceptions import ConfiguracionError


@dataclass(frozen=True)
class SharePointOrigenSettings:
    """App Registration del tenant 'BPO' (Sites.Selected sobre /sites/BPO).
    El site tiene un unico drive ('Documentos compartidos'): se resuelve por
    resolve_default_drive(), no por nombre."""

    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    folder_path: str
    timeout_ms: int = 120000


@dataclass(frozen=True)
class SharePointDestinoSettings:
    """App Registration del tenant 'ReportingFractalia' (Sites.Selected sobre
    /sites/ReportingFractalia), drive 'Data Reporting'."""

    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    drive_name: str
    folder_path: str
    timeout_ms: int = 120000


@dataclass(frozen=True)
class DbSettings:
    """SQL Server 'CL_MOVIL' (172.17.0.162), destino de cargar_correos.py.
    Separado de Settings/cargar_configuracion() (igual que
    SharePointOrigenSettings/cargar_configuracion_origen() en 02_ventas):
    main.py/verificar_copia.py no necesitan estas variables, solo
    cargar_correos.py."""

    server: str
    database: str
    user: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "no"
    trust_server_certificate: str = "yes"
    batch_size: int = 5000


@dataclass(frozen=True)
class Settings:
    origen: SharePointOrigenSettings
    destino: SharePointDestinoSettings
    log_dir: Path = Path("logs")
    # Periodo de carga de cargar_correos.py (FechaHora_UTC_Texto, UTC ISO-8601).
    # Sin parsear/validar aqui -- eso lo hace cargar_correos._parse_fecha_utc().
    # No usado por main.py ni verificar_copia.py.
    fecha_inicio: str | None = None
    fecha_fin: str | None = None


def _require_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise ConfiguracionError(f"La variable de entorno '{nombre}' es obligatoria. Ver .env.example.")
    return valor


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(
    base_dir: Path, fecha_inicio: str | None = None, fecha_fin: str | None = None
) -> Settings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuracion.

    'fecha_inicio'/'fecha_fin' permiten sobrescribir por linea de comandos
    (ver cargar_correos.py --fecha-inicio/--fecha-fin) el periodo definido en
    '.env' (FECHA_INICIO/FECHA_FIN) -- mismo patron que 'fecha'/VAR_FECHA en
    02_ventas/config.py."""
    load_dotenv(base_dir / ".env")

    origen = SharePointOrigenSettings(
        tenant_id=_require_env("SOURCE_TENANT_ID"),
        client_id=_require_env("SOURCE_CLIENT_ID"),
        client_secret=_require_env("SOURCE_CLIENT_SECRET"),
        hostname=os.getenv("SOURCE_SHAREPOINT_HOSTNAME", "fractaliagroup.sharepoint.com"),
        site_path=_require_env("SOURCE_SHAREPOINT_SITE_PATH"),
        folder_path=_require_env("SOURCE_SHAREPOINT_FOLDER_PATH"),
        timeout_ms=_env_int("SOURCE_GRAPH_TIMEOUT", 120000),
    )

    destino = SharePointDestinoSettings(
        tenant_id=_require_env("TENANT_ID"),
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
        hostname=os.getenv("SHAREPOINT_HOSTNAME", "fractaliagroup.sharepoint.com"),
        site_path=_require_env("SHAREPOINT_SITE_PATH"),
        drive_name=_require_env("SHAREPOINT_DRIVE_NAME"),
        folder_path=_require_env("SHAREPOINT_FOLDER_PATH"),
        timeout_ms=_env_int("GRAPH_TIMEOUT", 120000),
    )

    valor_inicio = fecha_inicio if fecha_inicio is not None else os.getenv("FECHA_INICIO")
    valor_fin = fecha_fin if fecha_fin is not None else os.getenv("FECHA_FIN")

    return Settings(
        origen=origen, destino=destino, log_dir=base_dir / "logs", fecha_inicio=valor_inicio, fecha_fin=valor_fin
    )


def cargar_configuracion_db(base_dir: Path) -> DbSettings:
    """Carga las credenciales de SQL Server ('CL_MOVIL'), usadas unicamente
    por cargar_correos.py."""
    load_dotenv(base_dir / ".env")
    return DbSettings(
        server=_require_env("DB_SERVER"),
        database=os.getenv("DB_NAME", "CL_MOVIL"),
        user=_require_env("DB_USER"),
        password=_require_env("DB_PASSWORD"),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        encrypt=os.getenv("DB_ENCRYPT", "no"),
        trust_server_certificate=os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes"),
        batch_size=_env_int("BATCH_SIZE", 5000),
    )
