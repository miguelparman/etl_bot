from datetime import date
from pathlib import Path

import pandas as pd

from etl_chile.application.use_cases import ventas_mappings as mappings
from etl_chile.application.use_cases.ventas_pipeline import VentasPipeline
from tests.unit.fakes import FakeDatabaseGateway, FakeSpreadsheetReader


def _fake_df_for_spec(spec, row_value="x"):
    columns = [mapping.source_column for mapping in spec]
    return pd.DataFrame([[row_value] * len(columns)], columns=columns)


def _build_pipeline():
    db = FakeDatabaseGateway()

    sheets = {
        mappings.BASEV2_SHEET: _fake_df_for_spec(mappings.BASEV2_COLUMN_SPEC),
        mappings.ESP_SHEET: _fake_df_for_spec(mappings.ESP_COLUMN_SPEC),
        mappings.SUP_SHEET: _fake_df_for_spec(mappings.SUP_COLUMN_SPEC),
        mappings.RANGO_COMISIONES_SHEET: _fake_df_for_spec(mappings.RANGO_COMISIONES_COLUMN_SPEC),
        mappings.METAS_COMISIONES_SHEET: _fake_df_for_spec(mappings.METAS_COMISIONES_COLUMN_SPEC),
        "DNI Senalizaciones$": pd.DataFrame(
            {"DNI ORIGEN": ["1"], "DNI A CAMBIAR": ["001"], "Observación": ["obs"]}
        ),
    }
    spreadsheet_reader = FakeSpreadsheetReader(sheets)

    db.tables[mappings.FUNNEL_VENTAS_TEMP_SOURCE_TABLE] = _fake_df_for_spec(
        mappings.FUNNEL_VENTAS_TEMP_COLUMN_SPEC
    )

    pipeline = VentasPipeline(
        db=db,
        spreadsheet_reader=spreadsheet_reader,
        base_carta_meta_xlsx_path=Path("Base Carta Meta.xlsx"),
        funnel_ventas_v2_xlsx_path=Path("FUNNEL VENTAS V2.xlsx"),
    )
    return pipeline, db


def test_ventas_pipeline_runs_all_branches_and_writes_expected_tables():
    pipeline, db = _build_pipeline()

    pipeline.run(fecha=date(2026, 1, 1))

    for table in (
        mappings.RANGO_COMISIONES_TABLE,
        "TBL_FUNNEL_SENHALIZACIONES_DNI",
        mappings.METAS_COMISIONES_TABLE,
        mappings.BASEV2_TABLE,
        mappings.ESP_TABLE,
        mappings.SUP_TABLE,
        mappings.FUNNEL_VENTAS_TEMP_TABLE,
    ):
        assert table in db.inserted, f"no se insertaron datos en {table}"

    assert any("INSERT INTO [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS2]" in s for s in db.executed_sql)
