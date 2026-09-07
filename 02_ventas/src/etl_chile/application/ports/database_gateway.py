"""Puerto (interfaz) hacia la base de datos SQL Server.

Equivalente al conjunto de Execute SQL Task + OLE DB Destination (fast load)
de los paquetes SSIS. La capa de aplicacion depende solo de esta interfaz;
la implementacion concreta vive en infrastructure/db.
"""

from __future__ import annotations

from typing import Protocol, Sequence

import pandas as pd


class DatabaseGateway(Protocol):
    def execute(self, sql: str, params: dict | None = None) -> None:
        """Ejecuta una unica sentencia SQL (equivalente a un Execute SQL Task simple)."""
        ...

    def execute_batch(self, statements: Sequence[str]) -> None:
        """Ejecuta varias sentencias en orden dentro de una misma transaccion.

        Equivalente a un Execute SQL Task cuyo SqlStatementSource contiene
        varios batches separados por 'GO'.
        """
        ...

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        """Equivalente a un Execute SQL Task 'TRUNCATE TABLE [schema].[table]'."""
        ...

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> None:
        """Equivalente a un OLE DB Destination en modo fast-load."""
        ...

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        """Lee una tabla completa. Equivalente a un OLE DB Source en modo tabla."""
        ...
