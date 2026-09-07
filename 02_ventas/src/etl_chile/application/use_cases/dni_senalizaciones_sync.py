"""Sincronizacion de TBL_FUNNEL_SENHALIZACIONES_DNI desde 'Base Carta Meta.xlsx'.

Este paso aparece IDENTICO en ambos paquetes SSIS originales:
- CROSS 0101 SSIS_CL_Senalizaciones.dtsx -> Data Flow "TBL_FUNNEL_SENHALIZACIONES_DNI"
  (dentro de "Contenedor de secuencias")
- CROSS 0102 SSIS_CL_Ventas.dtsx -> Data Flow "TBL_FUNNEL_SENHALIZACIONES_DNI"
  (dentro de "Contenedor de secuencias 2\\Contenedor de secuencias 1")

Ambos truncan la misma tabla y la recargan desde la misma hoja Excel, por lo
que en esta migracion se extrae como un unico caso de uso reutilizable en
lugar de duplicar el codigo en los dos pipelines.
"""

from __future__ import annotations

from pathlib import Path

from etl_chile.application.ports.database_gateway import DatabaseGateway
from etl_chile.application.ports.spreadsheet_reader import SpreadsheetReader
from etl_chile.application.use_cases.column_transform import apply_column_spec
from etl_chile.domain.column_spec import CastType, ColumnMapping

DNI_SENALIZACIONES_SHEET = "DNI Senalizaciones$"
DNI_SENALIZACIONES_TABLE = "TBL_FUNNEL_SENHALIZACIONES_DNI"

DNI_SENALIZACIONES_COLUMN_SPEC = (
    ColumnMapping("DNI ORIGEN", "DNI ORIGEN", CastType.STR),
    ColumnMapping("DNI A CAMBIAR", "DNI A CAMBIAR", CastType.STR),
    ColumnMapping("Observación", "Observación", CastType.STR),
)


def sync_dni_senalizaciones(
    db: DatabaseGateway,
    spreadsheet_reader: SpreadsheetReader,
    base_carta_meta_path: Path,
) -> None:
    """TRUNCATE + reload de TBL_FUNNEL_SENHALIZACIONES_DNI."""
    db.truncate_table(DNI_SENALIZACIONES_TABLE)

    raw = spreadsheet_reader.read_sheet(base_carta_meta_path, DNI_SENALIZACIONES_SHEET)
    transformed = apply_column_spec(raw, DNI_SENALIZACIONES_COLUMN_SPEC)
    db.bulk_insert(DNI_SENALIZACIONES_TABLE, transformed)
