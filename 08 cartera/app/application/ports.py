"""Puertos (interfaces) que la capa de aplicacion necesita para orquestar el
pipeline, sin conocer la tecnologia concreta (pyodbc, pandas, el archivo
Excel concreto, ...) que los implementa. Las implementaciones reales viven en
app/infrastructure/.

pandas.DataFrame se usa como el "idioma" comun de datos tabulares entre capas
(equivalente a los buffers de fila que SSIS pasa entre componentes del Data
Flow).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, Sequence

import pandas as pd


class DatabaseGateway(Protocol):
    """Equivalente a un Connection Manager OLE DB del paquete original, mas
    las tareas Execute SQL / Data Flow que corren sobre el.

    El pipeline usa DOS instancias de este puerto -- una por cada Connection
    Manager del .dtsx original (CL_CARTERA y CL_TEMPORALES) -- igual que el
    paquete SSIS tenia dos Connection Managers OLE DB independientes.
    """

    def execute_script(self, sql: str, params: Sequence[Any] | None = None) -> None:
        """Ejecuta un script T-SQL completo (una o mas sentencias, sin 'GO')
        como un unico batch. Equivalente a un Execute SQL Task simple o
        multi-sentencia del paquete original."""
        ...

    def fetch_scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        """Ejecuta una consulta escalar (p.ej. SELECT COUNT(*) ...) y
        devuelve el primer valor de la primera fila. Equivalente a evaluar la
        condicion de un 'IF EXISTS (...)' del paquete original."""
        ...

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        """Equivalente a un Execute SQL Task 'TRUNCATE TABLE [schema].[table]'."""
        ...

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> int:
        """Equivalente a un OLE DB Destination en modo fast-load. Devuelve la
        cantidad de filas insertadas."""
        ...

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        """Lee una tabla completa. Equivalente a un OLE DB Source en modo
        tabla (AccessMode=0)."""
        ...


class SpreadsheetReader(Protocol):
    """Equivalente al Connection Manager Excel ('CARTERA') del paquete original."""

    def read_sheet(self, path: Path, sheet_name: str) -> pd.DataFrame:
        """Devuelve la hoja completa, sin tipar ni sanear (eso lo hace la
        capa application, en extraction.py)."""
        ...
