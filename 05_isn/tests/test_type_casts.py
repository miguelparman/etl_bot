import polars as pl
import pytest

from src.transform.type_casts import ConversionError, apply_envios_consolidado_casts

BASE_ROW = {
    "FECHA_EVENTO": "20260814",
    "Número del caso": "12345",
    "SUBSEGMENTO": "PYME",
}


def _df(**overrides) -> pl.DataFrame:
    row = {**BASE_ROW, **overrides}
    return pl.DataFrame([row])


def test_valid_row_is_cast_without_error():
    df = apply_envios_consolidado_casts(_df())
    assert df["FECHA_EVENTO"].dtype == pl.Int32
    assert df["Número del caso"].dtype == pl.Int32
    assert df["FECHA_EVENTO"][0] == 20260814


def test_non_numeric_fecha_evento_fails_like_ssis_failcomponent():
    with pytest.raises(ConversionError):
        apply_envios_consolidado_casts(_df(FECHA_EVENTO="no-es-fecha"))


def test_non_numeric_numero_caso_fails():
    with pytest.raises(ConversionError):
        apply_envios_consolidado_casts(_df(**{"Número del caso": "ABC"}))


def test_subsegmento_over_20_chars_fails_instead_of_truncating():
    with pytest.raises(ConversionError):
        apply_envios_consolidado_casts(
            _df(SUBSEGMENTO="X" * 21)
        )


def test_subsegmento_exactly_20_chars_is_allowed():
    df = apply_envios_consolidado_casts(_df(SUBSEGMENTO="X" * 20))
    assert df["SUBSEGMENTO"][0] == "X" * 20
