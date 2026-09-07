"""
Reemplaza los componentes Microsoft.OLEDBDestination (FastLoad/TABLOCK) de
ambos paquetes.

`load_dataframe` usa pyodbc directo (ver db.py::get_raw_pyodbc_connection) en
vez de pandas.to_sql: con pandas.to_sql + SQLAlchemy 2.x, el "insertmanyvalues"
que arma para tablas anchas dificultaba diagnosticar errores de datos reales
(mensajes de error poco claros, ver historial de este archivo). Con pyodbc
directo se recupera el control fino que tenía el Data Flow original:

- `WITH (TABLOCK)` en el INSERT, igual que `FastLoadOptions=TABLOCK,...` del
  OLE DB Destination.
- Envío en lotes de `ROWS_PER_BATCH=5000` (mismo valor que trae el .dtsx).
- UN SOLO commit al final de toda la carga (o rollback completo si algo
  falla), igual que `FastLoadMaxInsertCommitSize=2147483647` -- SSIS lo
  configuró tan alto que en la práctica es "no confirmar hasta el final".

Se comparte entre contactos/ e isn/ porque en ambos .dtsx el patrón de carga
es idéntico: TRUNCATE (o DROP+SELECT INTO, manejado aparte en sql/) seguido
de una carga masiva a una tabla ya existente.
"""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import text

from db import get_connection, get_raw_pyodbc_connection

logger = logging.getLogger(__name__)


def truncate_table(database: str, table: str, schema: str = "dbo") -> None:
    logger.info("TRUNCATE %s.%s.%s", database, schema, table)
    with get_connection(database) as conn:
        conn.execute(text(f"TRUNCATE TABLE [{schema}].[{table}]"))


def _a_valor_pyodbc(valor):
    """Convierte NA/NaT/pd.NA/NaN a None y tipos numpy (Int64/etc.) a int/float
    nativos de Python -- pyodbc no siempre reconoce subclases de numpy."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(valor, (int, float, str)):
        return valor
    if hasattr(valor, "item"):  # numpy.int64, numpy.float64, etc.
        return valor.item()
    return valor


def load_dataframe(
    database: str,
    df: pd.DataFrame,
    table: str,
    schema: str = "dbo",
    batch_size: int = 5000,  # = ROWS_PER_BATCH del FastLoadOptions original
) -> int:
    if df.empty:
        logger.info("Sin filas para cargar en %s.%s.%s", database, schema, table)
        return 0

    columnas = list(df.columns)
    columnas_sql = ", ".join(f"[{c}]" for c in columnas)
    placeholders = ", ".join("?" for _ in columnas)
    # WITH (TABLOCK) = FastLoadOptions="TABLOCK,..." del OLE DB Destination original.
    insert_sql = f"INSERT INTO [{schema}].[{table}] WITH (TABLOCK) ({columnas_sql}) VALUES ({placeholders})"

    filas = [tuple(_a_valor_pyodbc(v) for v in fila) for fila in df.itertuples(index=False, name=None)]

    logger.info("Cargando %d filas en %s.%s.%s (lotes de %d, un solo commit al final)", len(filas), database, schema, table, batch_size)
    total_insertadas = 0
    # Un solo commit al final (o rollback completo si algo falla) = mismo
    # comportamiento que FastLoadMaxInsertCommitSize=2147483647 del .dtsx.
    with get_raw_pyodbc_connection(database) as conn:
        cursor = conn.cursor()
        # fast_executemany=True agrupa cada lote en menos viajes de red (10-50x
        # más rápido que executemany fila por fila) -- es seguro reactivarlo acá
        # porque ya se truncan/validan los anchos de columna ANTES de llegar acá
        # (ver contactos/transformer.py y contactos/validator.py): el problema
        # real que llevó a desactivarlo no era un bug de pyodbc, era que un dato
        # real excedía el ancho declarado de la columna destino.
        cursor.fast_executemany = True
        try:
            total_lotes = -(-len(filas) // batch_size)  # ceil
            for numero_lote, inicio in enumerate(range(0, len(filas), batch_size), start=1):
                lote = filas[inicio : inicio + batch_size]
                cursor.executemany(insert_sql, lote)
                total_insertadas += len(lote)
                if numero_lote % 10 == 0 or numero_lote == total_lotes:
                    logger.info(
                        "%s.%s.%s: %d/%d filas enviadas (lote %d/%d, aún sin confirmar)",
                        database, schema, table, total_insertadas, len(filas), numero_lote, total_lotes,
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception(
                "Fallo cargando %s.%s.%s -- se revirtió TODA la carga (0 filas confirmadas), "
                "igual que haría el FastLoad original con MaxInsertCommitSize tan alto.",
                database, schema, table,
            )
            raise
        finally:
            cursor.close()

    logger.info("Carga completada en %s.%s.%s (%d filas)", database, schema, table, total_insertadas)
    return total_insertadas
