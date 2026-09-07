"""Dobles de prueba (fakes) para los puertos de la capa application.

Permiten testear los pipelines sin una base de datos ni archivos Excel
reales, registrando las llamadas para poder aseverar el orden/contenido.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class FakeDatabaseGateway:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []
        self.executed_batches: list[list[str]] = []
        self.truncated_tables: list[str] = []
        self.inserted: dict[str, pd.DataFrame] = {}
        self.tables: dict[str, pd.DataFrame] = {}

    def execute(self, sql: str, params: dict | None = None) -> None:
        self.executed_sql.append(sql)

    def execute_batch(self, statements) -> None:
        self.executed_batches.append(list(statements))

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        self.truncated_tables.append(table)

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> None:
        self.inserted[table] = df

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        return self.tables[table]


class FakeSpreadsheetReader:
    def __init__(self, sheets: dict[str, pd.DataFrame]) -> None:
        self._sheets = sheets

    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        return self._sheets[sheet_name]


class FakeFlatFileReader:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def read_csv(self, path: Path, column_names=None) -> pd.DataFrame:
        return self._df


class FakeCsvDownloader:
    def __init__(self) -> None:
        self.download_called = False

    def download(self) -> Path:
        self.download_called = True
        return Path("fake.csv")
