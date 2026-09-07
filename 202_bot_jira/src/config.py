"""Carga de configuración (variables de entorno y argumentos de CLI)."""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_user: str
    jira_password: str
    tz: ZoneInfo
    template_path: str


def load_settings(argv: list) -> Settings:
    load_dotenv(BASE_DIR / ".env")
    template_path = argv[1] if len(argv) > 1 else str(BASE_DIR / "worklog.xlsx")
    return Settings(
        jira_base_url=os.environ["JIRA_BASE_URL"].rstrip("/"),
        jira_user=os.environ["JIRA_USER"],
        jira_password=os.environ["JIRA_PASSWORD"],
        tz=ZoneInfo("America/Lima"),
        template_path=template_path,
    )
