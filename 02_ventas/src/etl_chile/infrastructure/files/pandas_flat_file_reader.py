"""Implementacion concreta del puerto FlatFileReader usando pandas.

Sustituye al Connection Manager FLATFILE y al componente Flat File Source
del paquete de Señalizaciones (CSV delimitado por comas, UTF-8, con
cabecera en la primera fila).
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd


class PandasFlatFileReader:
    def read_csv(self, path: Path, column_names: Sequence[str] | None = None) -> pd.DataFrame:
        if column_names is not None:
            # Posicional, como el Flat File Source de SSIS: se descarta el
            # encabezado real del archivo y se asignan los nombres fijos del
            # Connection Manager por posicion.
            return pd.read_csv(
                path, encoding="utf-8", header=0, names=list(column_names)
            )
        return pd.read_csv(path, encoding="utf-8")
