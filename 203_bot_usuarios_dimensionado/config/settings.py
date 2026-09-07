"""Capa de configuracion: carga .env y expone los datos que necesita el bot."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


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
    destino: Path


def cargar_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")

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
        destino=Path(
            r"D:\IRISCENE ENGINEERING CORPORATION SLU\Repositorio Bi - Reporting_BPO"
            r"\BPO_Chile\9. Dimensionamiento_y_Programación\Bases"
            r"\PVTA_PROYECCION_PPP_FRACTALIA_PERU.csv"
        ),
    )
