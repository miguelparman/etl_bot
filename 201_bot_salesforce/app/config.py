"""
Configuracion centralizada de la aplicacion.

Todos los valores sensibles y ajustables (credenciales, timeouts, rutas,
flags de comportamiento) se leen desde variables de entorno (.env) y se
exponen aqui como un unico objeto `settings`. Ningun otro modulo debe leer
os.environ directamente ni hardcodear timeouts/rutas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Carpeta local/de red adicional donde tambien se copia cada informe
# descargado, ademas de subirlo a SharePoint. Puede sobreescribirse con
# LOCAL_COPY_DIR en .env si esta ruta cambia entre equipos.
_DEFAULT_LOCAL_COPY_DIR = Path(
    r"D:\IRISCENE ENGINEERING CORPORATION SLU\BPO - Insumos\Chile\SEGUIMIENTO"
)

# Subcarpeta de SharePoint usada por defecto por los informes que no
# declaran su propia "sharepoint_folder_path" en config/reports.py. Puede
# sobreescribirse con SHAREPOINT_FOLDER_PATH en .env.
_DEFAULT_SHAREPOINT_FOLDER_PATH = "REPOSITORIOS DE CRUDOS/CHILE/BPOCHIPE/01 SEGUIMIENTO"


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value and value.strip() else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value.strip())


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria '{name}'. "
            f"Revisa tu archivo .env (usa .env.example como referencia)."
        )
    return value


@dataclass(frozen=True)
class Settings:
    # --- Microsoft Graph / Entra ID ---
    tenant_id: str
    client_id: str
    client_secret: str

    # --- Salesforce ---
    salesforce_username: str
    salesforce_password: str
    salesforce_domain: str = "https://telefonicab2b.lightning.force.com"

    # --- SharePoint: resolucion de site/drive/folder por ruta ---
    sharepoint_hostname: str = "fractaliagroup.sharepoint.com"
    sharepoint_site_path: str = "/sites/ReportingFractalia"
    sharepoint_drive_name: str = "Data Reporting"
    sharepoint_folder_path: str = _DEFAULT_SHAREPOINT_FOLDER_PATH

    # IDs cacheados opcionalmente tras la primera resolucion (evitan 3
    # llamadas a Graph en cada ejecucion). Si estan vacios se resuelven
    # dinamicamente y se recomienda registrarlos en .env despues.
    sharepoint_site_id: str = ""
    sharepoint_drive_id: str = ""
    sharepoint_folder_id: str = ""

    # --- Comportamiento ---
    headless: bool = True
    max_retries: int = 3
    delete_local_after_upload: bool = True
    overwrite_existing: bool = True
    max_reports: int = 0  # 0 o vacio = procesar todos
    dry_run: bool = False

    # --- Timeouts (todos en milisegundos, salvo que se indique lo contrario) ---
    page_timeout_ms: int = 60_000
    download_timeout_ms: int = 120_000
    graph_timeout_ms: int = 120_000
    manual_login_timeout_minutes: int = 10

    # --- Rutas locales ---
    base_dir: Path = field(default_factory=lambda: BASE_DIR)
    downloads_dir: Path = field(default_factory=lambda: BASE_DIR / "downloads")
    logs_dir: Path = field(default_factory=lambda: BASE_DIR / "logs")
    screenshots_dir: Path = field(default_factory=lambda: BASE_DIR / "screenshots")
    auth_state_path: Path = field(
        default_factory=lambda: BASE_DIR / "playwright" / ".auth" / "sf_state.json"
    )
    local_copy_dir: Path = field(default_factory=lambda: _DEFAULT_LOCAL_COPY_DIR)

    def sensitive_values(self) -> list[str]:
        """Valores que nunca deben aparecer en logs, tal cual, en texto plano."""
        return [self.client_secret, self.salesforce_password]

    def ensure_directories(self) -> None:
        for directory in (
            self.downloads_dir,
            self.logs_dir,
            self.screenshots_dir,
            self.auth_state_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    settings = Settings(
        tenant_id=_require("TENANT_ID"),
        client_id=_require("CLIENT_ID"),
        client_secret=_require("CLIENT_SECRET"),
        salesforce_username=_require("SALESFORCE_USERNAME"),
        salesforce_password=_require("SALESFORCE_PASSWORD"),
        sharepoint_folder_path=_env_str("SHAREPOINT_FOLDER_PATH", _DEFAULT_SHAREPOINT_FOLDER_PATH),
        sharepoint_site_id=os.environ.get("SHAREPOINT_SITE_ID", ""),
        sharepoint_drive_id=os.environ.get("SHAREPOINT_DRIVE_ID", ""),
        sharepoint_folder_id=os.environ.get("SHAREPOINT_FOLDER_ID", ""),
        headless=_env_bool("HEADLESS", True),
        max_retries=_env_int("MAX_RETRIES", 3),
        delete_local_after_upload=_env_bool("DELETE_LOCAL_AFTER_UPLOAD", True),
        overwrite_existing=_env_bool("OVERWRITE_EXISTING", True),
        max_reports=_env_int("MAX_REPORTS", 0),
        dry_run=_env_bool("DRY_RUN", False),
        page_timeout_ms=_env_int("PAGE_TIMEOUT", 60_000),
        download_timeout_ms=_env_int("DOWNLOAD_TIMEOUT", 120_000),
        graph_timeout_ms=_env_int("GRAPH_TIMEOUT", 120_000),
        manual_login_timeout_minutes=_env_int("MANUAL_LOGIN_TIMEOUT_MINUTES", 10),
        local_copy_dir=(
            Path(os.environ["LOCAL_COPY_DIR"]) if os.environ.get("LOCAL_COPY_DIR", "").strip() else _DEFAULT_LOCAL_COPY_DIR
        ),
    )
    settings.ensure_directories()
    return settings


settings = load_settings()
