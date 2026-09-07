"""Modelos de dominio: value objects sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportSettings:
    """Parámetros que gobiernan un proceso de exportación (agnósticos de Playwright)."""

    report_url: str
    report_page_name: str
    table_visual_name: str
    destino_final: Path

    # Filtros (slicers) a aplicar antes de exportar. Vacío ("") = no tocar
    # ese filtro y dejar el que traiga el informe. Se cambian cada mes.
    filtro_anio: str
    filtro_mes_nc: str
    filtro_proveedor: str

    headless: bool
    slow_mo: int

    nav_timeout: int
    visual_timeout: int
    menu_timeout: int
    download_timeout: int
    login_poll_timeout: int

    profile_dir: Path
    screenshots_dir: Path
    descargas_dir: Path
    log_file: Path


@dataclass(frozen=True)
class ExportResult:
    """Resultado de una exportación (Extract + Load) exitosa."""

    ruta_archivo: Path
