"""Implementacion concreta del puerto DatabaseGateway para SQL Server."""

from __future__ import annotations

import logging
from typing import Sequence

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Rango valido por tipo de fecha/hora de SQL Server. SMALLDATETIME en
# particular es mucho mas angosto que DATETIME (1900-2079 vs 1753-9999); un
# valor real fuera de ese rango (typo de digitacion, ano mal parseado, etc.)
# rompe el INSERT con "Datetime field overflow" si no se recorta antes.
# DATE/DATETIME2 no se listan: su rango (0001-9999) nunca es un problema
# practico.
_DATETIME_BOUNDS: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
    "SMALLDATETIME": (pd.Timestamp("1900-01-01"), pd.Timestamp("2079-06-06 23:59:00")),
    "DATETIME": (pd.Timestamp("1753-01-01"), pd.Timestamp("9999-12-31 23:59:59.997")),
}


class SqlServerGateway:
    """Adaptador de infraestructura: implementa DatabaseGateway con SQLAlchemy/pyodbc."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def execute(self, sql: str, params: dict | None = None) -> None:
        with self._engine.begin() as conn:
            conn.execute(text(sql), params or {})

    def execute_batch(self, statements: Sequence[str]) -> None:
        with self._engine.begin() as conn:
            for statement in statements:
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))

    def truncate_table(self, table: str, schema: str = "dbo") -> None:
        self.execute(f"TRUNCATE TABLE [{schema}].[{table}]")

    def bulk_insert(self, table: str, df: pd.DataFrame, schema: str = "dbo") -> None:
        if df.empty:
            logger.warning("bulk_insert: DataFrame vacio para %s.%s, no se inserta nada", schema, table)
            return

        df = self._sanitize_for_target_schema(table, df, schema)

        # No se usa method="multi": arma un unico INSERT con multiples VALUES,
        # y SQL Server limita a 2100 parametros POR SENTENCIA. Con tablas
        # anchas (30+ columnas) eso se supera con pocos cientos de filas y
        # desborda ademas el contador interno de pyodbc (queda negativo).
        # Sin `method`, SQLAlchemy usa executemany fila a fila, acelerado por
        # `fast_executemany=True` del engine (ver sqlserver_engine.py) -- un
        # unico round-trip igualmente rapido, sin el limite de parametros.
        df.to_sql(
            table,
            self._engine,
            schema=schema,
            if_exists="append",
            index=False,
            chunksize=1000,
        )

    def read_table(self, table: str, schema: str = "dbo") -> pd.DataFrame:
        return pd.read_sql_table(table, self._engine, schema=schema)

    def _sanitize_for_target_schema(
        self, table: str, df: pd.DataFrame, schema: str
    ) -> pd.DataFrame:
        """Ajusta el DataFrame al esquema REAL de la tabla destino en SQL Server.

        Los anchos/tipos declarados en los Connection Manager/Data Conversion
        del .dtsx original son una foto de hace anios; los datos "en vivo"
        (texto libre cargado por usuarios, fechas mal digitadas) pueden haber
        crecido o salido de rango desde entonces y romper el INSERT con
        "String data, right truncation" o "Datetime field overflow". Se
        recorta/anula en vez de fallar, dejando rastro en el log --
        consistente con el resto de los cast permisivos de esta capa (ver
        column_transform.py).
        """
        try:
            columns_metadata = inspect(self._engine).get_columns(table, schema=schema)
        except Exception:  # noqa: BLE001 - si no se puede reflejar, se inserta sin ajustar
            logger.warning(
                "No se pudo leer el esquema de %s.%s para validar tipos/anchos",
                schema,
                table,
            )
            return df

        for col in columns_metadata:
            column_name = col["name"]
            if column_name not in df.columns:
                continue

            max_length = getattr(col["type"], "length", None)
            if max_length:
                df[column_name] = self._truncate_text_column(
                    table, column_name, df[column_name], max_length
                )
                continue

            if not pd.api.types.is_datetime64_any_dtype(df[column_name]):
                continue

            type_name = type(col["type"]).__name__.upper()
            bounds = _DATETIME_BOUNDS.get(type_name)
            if bounds:
                df[column_name] = self._clip_datetime_column(
                    table, column_name, df[column_name], type_name, *bounds
                )

            if type_name == "DATE":
                # pyodbc + fast_executemany tiene un bug conocido al bindear
                # un datetime/Timestamp (con componente de hora, aunque sea
                # 00:00:00) contra una columna DATE nativa: reporta
                # "Datetime field overflow" incluso con fechas validas. Se
                # convierte a datetime.date puro (NaT -> None) antes de
                # insertar.
                df[column_name] = df[column_name].dt.date.where(
                    df[column_name].notna(), None
                )

        return df

    @staticmethod
    def _truncate_text_column(
        table: str, column_name: str, series: pd.Series, max_length: int
    ) -> pd.Series:
        if series.dtype != object and str(series.dtype) != "string":
            return series

        too_long = series.str.len() > max_length
        too_long = too_long.fillna(False)
        if too_long.any():
            logger.warning(
                "%s.%s: %d valor(es) exceden el ancho de columna (%d) y se truncan",
                table,
                column_name,
                int(too_long.sum()),
                max_length,
            )
            series = series.where(~too_long, series.str.slice(0, max_length))
        return series

    @staticmethod
    def _clip_datetime_column(
        table: str,
        column_name: str,
        series: pd.Series,
        type_name: str,
        min_value: pd.Timestamp,
        max_value: pd.Timestamp,
    ) -> pd.Series:
        out_of_range = (series < min_value) | (series > max_value)
        out_of_range = out_of_range.fillna(False)
        if out_of_range.any():
            logger.warning(
                "%s.%s: %d valor(es) fuera del rango valido de %s (%s..%s) se anulan (NULL)",
                table,
                column_name,
                int(out_of_range.sum()),
                type_name,
                min_value.date(),
                max_value.date(),
            )
            series = series.mask(out_of_range)
        return series
