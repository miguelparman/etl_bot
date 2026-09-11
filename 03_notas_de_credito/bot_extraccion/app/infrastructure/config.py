"""Adaptador de infraestructura: arma ExportSettings a partir de variables
de entorno (archivo '.env'), con valores por defecto si no están definidas."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.domain.models import ExportSettings

_DEFAULT_REPORT_URL = (
    "https://app.powerbi.com/groups/me/reports/"
    "1288f632-29dc-4065-b5a9-55a3fe3a023f/ReportSection?experience=power-bi"
)
_DEFAULT_DESTINO_FINAL = (
    r"D:\OneDrive - IRISCENE ENGINEERING CORPORATION SLU\Insumos Chile\Informes\NC\DB\NC_.xlsx"
)


def _env_bool(nombre: str, default: bool) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí"}


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return default
    return int(valor)


def cargar_configuracion(base_dir: Path) -> ExportSettings:
    """Carga '.env' (si existe, junto a main.py) y arma la configuración del dominio."""
    load_dotenv(base_dir / ".env")
    # ANIO/MES ya no se definen aquí como FILTRO_ANIO/FILTRO_MES_NC: viven en
    # el .env general del pipeline (carpeta padre), compartido con etl_carga.
    # Se carga como respaldo (no pisa lo que ya esté en el entorno, p. ej.
    # inyectado por el orquestador raíz con --anio/--mes).
    load_dotenv(base_dir.parent / ".env")

    return ExportSettings(
        report_url=os.getenv("REPORT_URL", _DEFAULT_REPORT_URL),
        report_page_name=os.getenv("REPORT_PAGE_NAME", "RESUMEN II"),
        table_visual_name=os.getenv("TABLE_VISUAL_NAME", "Detalle NC"),
        destino_final=Path(os.getenv("DESTINO_FINAL", _DEFAULT_DESTINO_FINAL)),
        filtro_anio=os.getenv("ANIO", os.getenv("FILTRO_ANIO", "")),
        filtro_mes_nc=os.getenv("MES", os.getenv("FILTRO_MES_NC", "")),
        filtro_proveedor=os.getenv("FILTRO_PROVEEDOR", ""),
        headless=_env_bool("HEADLESS", True),
        slow_mo=_env_int("SLOW_MO", 0),
        nav_timeout=_env_int("NAV_TIMEOUT", 90_000),
        visual_timeout=_env_int("VISUAL_TIMEOUT", 60_000),
        menu_timeout=_env_int("MENU_TIMEOUT", 15_000),
        download_timeout=_env_int("DOWNLOAD_TIMEOUT", 120_000),
        login_poll_timeout=_env_int("LOGIN_POLL_TIMEOUT", 300_000),
        profile_dir=base_dir / "playwright_profile",
        screenshots_dir=base_dir / "screenshots",
        descargas_dir=base_dir / "descargas_temp",
        log_file=base_dir / "export_nc_mipyme.log",
    )
