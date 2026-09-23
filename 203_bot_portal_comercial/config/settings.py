"""Capa de configuracion: carga .env y expone los datos que necesita el bot."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class SharePointDestino:
    """Carpeta de SharePoint + App Registration con permiso sobre ese sitio.
    drive_name vacio = drive por defecto del site (caso 'BPO')."""

    nombre: str
    tenant_id: str
    client_id: str
    client_secret: str
    hostname: str
    site_path: str
    drive_name: str
    folder_path: str


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    log_dir: Path
    portal_url: str
    portal_usuario: str
    portal_password: str
    headless: bool
    archivo_objetivo: str
    carpeta_fractalia: str
    ruta_post_venta: str
    ruta_dimensionamiento: str
    archivo_reporte_agentes: str
    destinos_sharepoint: tuple[SharePointDestino, ...]
    graph_timeout_ms: int


def _destino_sharepoint(nombre: str, prefijo: str) -> SharePointDestino:
    return SharePointDestino(
        nombre=nombre,
        tenant_id=os.environ[f"{prefijo}_TENANT_ID"],
        client_id=os.environ[f"{prefijo}_CLIENT_ID"],
        client_secret=os.environ[f"{prefijo}_CLIENT_SECRET"],
        hostname=os.environ[f"{prefijo}_SHAREPOINT_HOSTNAME"],
        site_path=os.environ[f"{prefijo}_SHAREPOINT_SITE_PATH"],
        drive_name=os.environ.get(f"{prefijo}_SHAREPOINT_DRIVE_NAME", "").strip(),
        folder_path=os.environ[f"{prefijo}_SHAREPOINT_FOLDER_PATH"],
    )


def cargar_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env", encoding="utf-8")

    return Settings(
        base_dir=BASE_DIR,
        log_dir=BASE_DIR / "logs",
        portal_url=os.environ["PORTAL_URL"],
        portal_usuario=os.environ["PORTAL_USUARIO"],
        portal_password=os.environ["PORTAL_PASSWORD"],
        headless=os.environ.get("HEADLESS", "true").strip().lower() != "false",
        archivo_objetivo="PVTA_PROYECCION_PPP_FRACTALIA_PERU.csv",
        carpeta_fractalia="#modulo59",
        ruta_post_venta="/00-REPORTES/CALLCENTER/FRACTALIA/POST VENTA/",
        ruta_dimensionamiento="/00-REPORTES/CALLCENTER/FRACTALIA/POST VENTA/DIMENSIONAMIENTO/",
        archivo_reporte_agentes="REPORTE_AGENTES_FRACTALIA_SEM.csv",
        # Destinos de ambos archivos. Solo ReportingFractalia: la app 'BPO' de Graph tiene permiso de solo
        # lectura sobre /sites/BPO (HTTP 403 al subir). Si se le otorga rol
        # 'write', basta agregar _destino_sharepoint("BPO", "BPO") aqui
        # (credenciales BPO_* ya estan en .env).
        destinos_sharepoint=(_destino_sharepoint("ReportingFractalia", "REPORTING"),),
        graph_timeout_ms=int(os.environ.get("GRAPH_TIMEOUT", "120000")),
    )
