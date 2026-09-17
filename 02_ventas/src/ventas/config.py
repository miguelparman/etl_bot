"""Arma la configuracion a partir de variables de entorno (archivo '.env').
Ninguna credencial vive en el codigo ni en este repositorio.

Equivalente al Connection Manager OLE DB 'CL_USUARIOS' (unico destino real
de ambos .dtsx -- '162.CL_DATA' esta declarado en 'CROSS 0102 SSIS_CL_Ventas'
pero ningun componente lo usa, ver README), a la configuracion de Microsoft
Graph que reemplaza, como ORIGEN, a los archivos de red locales/Google Drive
(carpeta '07 CROSS' de SharePoint), y a la variable de paquete 'User::Fecha'
de 'CROSS 0102 SSIS_CL_Ventas' (watermark de fecha para el ciclo
delete-then-reinsert de TBL_FUNNEL_VENTAS2, ver pipeline.py)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from exceptions import VentasError


@dataclass(frozen=True)
class DbSettings:
    """Equivalente al Connection Manager OLE DB 'CL_USUARIOS' (Provider MSOLEDBSQL.1)."""

    server: str
    database: str
    user: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "no"
    trust_server_certificate: str = "yes"


@dataclass(frozen=True)
class SharePointSettings:
    """App Registration de Microsoft Graph (permiso Sites.Selected sobre
    ReportingFractalia) que reemplaza, como ORIGEN, a los archivos de red
    local/Google Drive de los .dtsx originales: carpeta '07 CROSS'."""

    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    drive_name: str
    folder_path: str
    timeout_ms: int = 120000


@dataclass(frozen=True)
class SharePointOrigenSettings:
    """App Registration de Microsoft Graph para el sitio 'BPO', origen de
    'FUNNEL VENTAS V2.xlsx'. 'BPO' y 'ReportingFractalia' son tenants de
    Microsoft Entra DISTINTOS -- credenciales propias, no reutilizables con
    'SharePointSettings' arriba. Usado unicamente por
    copiar_funnel_ventas.py (paso 0); main.py nunca las necesita."""

    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    file_path: str
    timeout_ms: int = 120000


@dataclass(frozen=True)
class Settings:
    db: DbSettings
    sharepoint: SharePointSettings
    fecha: date | None  # User::Fecha (CROSS 0102 SSIS_CL_Ventas)
    batch_size: int = 5000
    log_file: Path = Path("ventas.log")


def _require_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise VentasError(f"La variable de entorno '{nombre}' es obligatoria. Ver .env.example.")
    return valor


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path, fecha: str | None = None) -> Settings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuracion.

    'fecha' (formato YYYY-MM-DD) permite sobrescribir por linea de comandos
    el valor de VAR_FECHA de '.env' -- igual que en SSIS se editaba a mano
    la expresion de la variable User::Fecha antes de cada corrida. Sin
    default embebido en el codigo (a diferencia del .dtsx original, que
    traia un literal fijo) -- ver README, 'Notas de fidelidad'.
    """
    load_dotenv(base_dir / ".env")

    db = DbSettings(
        server=_require_env("DB_SERVER"),
        database=os.getenv("DB_NAME", "CL_USUARIOS"),
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

    valor_fecha = fecha if fecha is not None else os.getenv("VAR_FECHA")

    return Settings(
        db=db,
        sharepoint=sharepoint,
        fecha=date.fromisoformat(valor_fecha) if valor_fecha else None,
        batch_size=_env_int("BATCH_SIZE", 5000),
        log_file=base_dir / "ventas.log",
    )


def cargar_configuracion_origen(base_dir: Path) -> SharePointOrigenSettings:
    """Carga las credenciales del tenant de origen ('BPO'), separadas de
    'cargar_configuracion()' porque main.py (el pipeline principal) nunca
    las necesita -- solo copiar_funnel_ventas.py (paso 0)."""
    load_dotenv(base_dir / ".env")
    return SharePointOrigenSettings(
        tenant_id=_require_env("SOURCE_TENANT_ID"),
        client_id=_require_env("SOURCE_CLIENT_ID"),
        client_secret=_require_env("SOURCE_CLIENT_SECRET"),
        hostname=os.getenv("SOURCE_SHAREPOINT_HOSTNAME", "fractaliagroup.sharepoint.com"),
        site_path=_require_env("SOURCE_SHAREPOINT_SITE_PATH"),
        file_path=_require_env("SOURCE_SHAREPOINT_FILE_PATH"),
        timeout_ms=_env_int("SOURCE_GRAPH_TIMEOUT", 120000),
    )
