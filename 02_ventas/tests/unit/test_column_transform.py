import pandas as pd

from etl_chile.application.use_cases.column_transform import apply_column_spec
from etl_chile.domain.column_spec import CastType, ColumnMapping


def test_apply_column_spec_renames_and_casts():
    df = pd.DataFrame(
        {
            "DNI ORIGEN": ["11111111", "22222222"],
            "Fecha Ingreso": ["2026-01-01", "2026-02-15"],
            "STB": ["1", "2"],
        }
    )
    spec = (
        ColumnMapping("DNI ORIGEN", "DNI_ORIGEN", CastType.STR),
        ColumnMapping("Fecha Ingreso", "FECHA_INGRESO", CastType.DATE),
        ColumnMapping("STB", "STB", CastType.INT),
    )

    result = apply_column_spec(df, spec)

    assert list(result.columns) == ["DNI_ORIGEN", "FECHA_INGRESO", "STB"]
    assert result["FECHA_INGRESO"].iloc[0] == pd.Timestamp("2026-01-01")
    assert result["STB"].iloc[1] == 2


def test_apply_column_spec_missing_source_column_raises():
    df = pd.DataFrame({"A": [1]})
    spec = (ColumnMapping("B", "B_DEST", CastType.NONE),)

    try:
        apply_column_spec(df, spec)
        assert False, "se esperaba KeyError"
    except KeyError:
        pass
