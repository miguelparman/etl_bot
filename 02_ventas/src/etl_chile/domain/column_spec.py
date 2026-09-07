"""Modelo de dominio para describir una transformacion de columnas.

Representa, de forma declarativa, lo que en los paquetes SSIS originales
hacian en conjunto un componente "Data Conversion" + el mapeo de columnas
de un "OLE DB Destination": para cada columna de origen, a que columna de
destino se escribe y que conversion de tipo se le aplica.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CastType(str, Enum):
    """Equivalente a los DataType usados por el componente Data Conversion."""

    STR = "str"
    DATE = "date"
    INT = "int"
    FLOAT = "float"
    NONE = "none"  # sin conversion, se copia el valor tal cual


@dataclass(frozen=True)
class ColumnMapping:
    """Una columna de origen -> una columna de destino, con su cast."""

    source_column: str
    destination_column: str
    cast: CastType = CastType.NONE


ColumnSpec = tuple[ColumnMapping, ...]
