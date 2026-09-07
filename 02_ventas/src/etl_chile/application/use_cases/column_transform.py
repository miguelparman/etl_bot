"""Logica de aplicacion: aplica un ColumnSpec a un DataFrame.

Es la regla de negocio comun a todos los Data Flow Tasks migrados: tomar las
columnas seleccionadas de una fuente (Excel/CSV/SQL), convertir su tipo
(equivalente al componente "Data Conversion" de SSIS) y renombrarlas a su
columna de destino final (equivalente al mapeo de columnas del OLE DB
Destination). Ambos pasos SSIS se colapsan aqui en uno solo por simplicidad,
sin cambiar el resultado final columna-a-columna.
"""

from __future__ import annotations

import logging

import pandas as pd

from etl_chile.domain.column_spec import CastType, ColumnSpec

logger = logging.getLogger(__name__)

# SQL Server no admite valores DATETIME fuera de este rango ("Datetime field
# overflow"). Texto de fecha ambiguo/incompleto (p.ej. "5/1" sin año) puede
# ser interpretado por dateutil con un año por defecto absurdo (año 1); en
# vez de dejar que eso reviente el INSERT, se anula (NaT) igual que un valor
# no parseable.
MIN_SQLSERVER_DATETIME = pd.Timestamp("1753-01-01")
MAX_SQLSERVER_DATETIME = pd.Timestamp("9999-12-31")


def apply_column_spec(df: pd.DataFrame, spec: ColumnSpec) -> pd.DataFrame:
    """Selecciona, castea y renombra columnas segun el spec declarativo.

    Los cast son deliberadamente permisivos (coerce -> NaN/NaT en vez de
    lanzar excepcion) porque el comportamiento estricto "FailComponent" de
    SSIS no tiene un equivalente practico deseable en un batch Python: es
    preferible cargar la fila con el valor nulo y dejar rastro en el log.
    """
    output_columns: dict[str, pd.Series] = {}

    for mapping in spec:
        if mapping.source_column not in df.columns:
            raise KeyError(
                f"La columna de origen '{mapping.source_column}' no existe en "
                f"el DataFrame leido. Columnas disponibles: {list(df.columns)}"
            )

        series = df[mapping.source_column]

        if mapping.cast is CastType.DATE:
            series = pd.to_datetime(series, errors="coerce", format="mixed")
            out_of_range = (series < MIN_SQLSERVER_DATETIME) | (series > MAX_SQLSERVER_DATETIME)
            if out_of_range.any():
                logger.warning(
                    "%s: %d valor(es) de fecha fuera de rango para SQL Server "
                    "se anulan (NULL)",
                    mapping.destination_column,
                    int(out_of_range.sum()),
                )
                series = series.mask(out_of_range)
        elif mapping.cast is CastType.INT:
            series = pd.to_numeric(series, errors="coerce").astype("Int64")
        elif mapping.cast is CastType.FLOAT:
            series = pd.to_numeric(series, errors="coerce")
        elif mapping.cast is CastType.STR:
            series = series.astype("string")
        # CastType.NONE: se copia el valor tal cual (passthrough)

        output_columns[mapping.destination_column] = series.reset_index(drop=True)

    return pd.DataFrame(output_columns)
