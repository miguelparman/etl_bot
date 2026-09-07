from datetime import date
from pathlib import Path

from src.config.settings import FilePathSettings


def _paths() -> FilePathSettings:
    return FilePathSettings(
        automatizado_dir=Path("C:/Automatizado"),
        aux_cliente_csv=Path("C:/aux_cliente.csv"),
        aux_contacto_csv=Path("C:/aux_contacto.csv"),
    )


def test_isn_source_csv_matches_original_connection_manager_path():
    paths = _paths()
    assert paths.isn_source_csv == Path("C:/Automatizado/Source/isn.csv")


def test_dated_archive_csv_matches_new_name_file_expression():
    paths = _paths()
    result = paths.dated_archive_csv(date(2026, 8, 14))
    assert result == Path("C:/Automatizado/PROSPECTOS_EMPRESA_20260814.csv")
