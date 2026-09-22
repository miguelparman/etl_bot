"""Tests de cargar_configuracion(): el periodo (FECHA_INICIO/FECHA_FIN) se
toma de '.env', pero un valor pasado explicitamente (--fecha-inicio/--fecha-fin
de cargar_correos.py) tiene prioridad -- mismo patron que 'fecha'/VAR_FECHA
en 02_ventas/config.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from config import cargar_configuracion

_ENV_MINIMO = """
SOURCE_TENANT_ID=t
SOURCE_CLIENT_ID=c
SOURCE_CLIENT_SECRET=s
SOURCE_SHAREPOINT_SITE_PATH=/sites/BPO
SOURCE_SHAREPOINT_FOLDER_PATH=Control Correos Chile
TENANT_ID=t2
CLIENT_ID=c2
CLIENT_SECRET=s2
SHAREPOINT_SITE_PATH=/sites/ReportingFractalia
SHAREPOINT_DRIVE_NAME=Data Reporting
SHAREPOINT_FOLDER_PATH=REPOSITORIOS DE CRUDOS/CHILE/BPOCHIPE/14 CORREOS
"""


@pytest.fixture
def base_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # cargar_configuracion() no limpia variables ya presentes en el proceso:
    # aislar FECHA_INICIO/FECHA_FIN entre tests.
    monkeypatch.delenv("FECHA_INICIO", raising=False)
    monkeypatch.delenv("FECHA_FIN", raising=False)
    (tmp_path / ".env").write_text(_ENV_MINIMO, encoding="utf-8")
    return tmp_path


def test_sin_env_ni_argumento_queda_none(base_dir: Path):
    settings = cargar_configuracion(base_dir)
    assert settings.fecha_inicio is None
    assert settings.fecha_fin is None


def test_toma_el_periodo_del_env(base_dir: Path):
    with open(base_dir / ".env", "a", encoding="utf-8") as f:
        f.write("\nFECHA_INICIO=2026-09-17T00:00:00\nFECHA_FIN=2026-09-23T00:00:00\n")

    settings = cargar_configuracion(base_dir)

    assert settings.fecha_inicio == "2026-09-17T00:00:00"
    assert settings.fecha_fin == "2026-09-23T00:00:00"


def test_argumento_explicito_tiene_prioridad_sobre_env(base_dir: Path):
    with open(base_dir / ".env", "a", encoding="utf-8") as f:
        f.write("\nFECHA_INICIO=2026-09-17T00:00:00\nFECHA_FIN=2026-09-23T00:00:00\n")

    settings = cargar_configuracion(base_dir, fecha_inicio="2026-10-01T00:00:00", fecha_fin="2026-10-02T00:00:00")

    assert settings.fecha_inicio == "2026-10-01T00:00:00"
    assert settings.fecha_fin == "2026-10-02T00:00:00"
