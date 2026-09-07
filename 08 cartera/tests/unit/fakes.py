"""Dobles de prueba (fakes) para los puertos de la capa application.

Permiten testear el pipeline sin una base de datos ni un archivo Excel
reales, registrando las llamadas para poder aseverar el orden/contenido --
igual que en los demas proyectos migrados de este repositorio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pandas as pd


class FakeDatabaseGateway:
    def __init__(self) -> None:
        self.executed_scripts: list[tuple[str, tuple]] = []
        self.truncated_tables: list[str] = []
        self.inserted: dict[str, pd.DataFrame] = {}
        self.tables: dict[str, pd.DataFrame] = {}
        # Config de test: texto exacto de la consulta -> valor devuelto por fetch_scalar.
        # Si la consulta no esta registrada, se devuelve 0 (equivalente a "control OK").
        self.scalars: dict[str, Any] = {}

    def execute_script(self, sql: str, params: Sequence[Any] | None = None) -> None:
        self.executed_scripts.append((sql, tuple(params) if params else ()))

    def fetch_scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        return self.scalars.get(sql, 0)

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        self.truncated_tables.append(table)

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> int:
        self.inserted[table] = df
        return len(df)

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        return self.tables[table]


class FakeSpreadsheetReader:
    def __init__(self, sheets: dict[str, pd.DataFrame]) -> None:
        self._sheets = sheets

    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        return self._sheets[sheet_name]
