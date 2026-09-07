"""Puerto (interfaz) para leer archivos planos (CSV).

Equivalente al componente Flat File Source (Microsoft.FlatFileSource).

Nota de fidelidad: el Flat File Connection Manager de SSIS declara un
esquema de columnas FIJO en tiempo de diseño y `ColumnNamesInFirstDataRow`
solo le indica que la primera fila del archivo es un encabezado A SALTAR —
SSIS nunca hace matching por el TEXTO del encabezado real del archivo, lee
por posicion. Por eso `read_csv` acepta `column_names`: cuando se pasa, se
ignora el texto del encabezado del archivo (que puede haber cambiado, p.ej.
si el CSV se genera desde una hoja de Google Sheets editada a mano) y se
asignan estos nombres por posicion, igual que hacia SSIS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

import pandas as pd


class FlatFileReader(Protocol):
    def read_csv(self, path: Path, column_names: Sequence[str] | None = None) -> pd.DataFrame:
        """Lee un CSV delimitado por comas como DataFrame.

        Si `column_names` se especifica, las columnas se asignan por
        posicion (ignorando el encabezado real del archivo), replicando el
        comportamiento del Flat File Source de SSIS.
        """
        ...
