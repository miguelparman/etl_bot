from pathlib import Path

import pandas as pd

from app.application import mappings
from app.application.extraction import CarteraExcelExtractor
from app.domain.exceptions import ExtraccionError
from app.domain.models import Periodo
from tests.unit.fakes import FakeSpreadsheetReader


def _fila_excel(**overrides) -> dict:
    fila = {col: "x" for col in mappings.EXCEL_COLUMNS}
    fila.update(overrides)
    return fila


def _build_extractor(df_hoja1: pd.DataFrame) -> CarteraExcelExtractor:
    reader = FakeSpreadsheetReader({mappings.EXCEL_SHEET: df_hoja1})
    return CarteraExcelExtractor(reader, Path("CARTERA_FRACTALIA.xlsx"))


def test_extraer_devuelve_las_26_columnas_de_staging_en_orden():
    df = pd.DataFrame([_fila_excel()])
    extractor = _build_extractor(df)

    resultado = extractor.extraer(Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert list(resultado.columns) == list(mappings.STAGING_INSERT_COLUMNS)


def test_extraer_descarta_rutcli_y_rut10():
    df = pd.DataFrame([_fila_excel()])
    extractor = _build_extractor(df)

    resultado = extractor.extraer(Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert "RUTCLI" not in resultado.columns
    assert "RUT10" not in resultado.columns


def test_extraer_trunca_segme_a_30_caracteres():
    valor_largo = "S" * 100
    df = pd.DataFrame([_fila_excel(SEGME=valor_largo)])
    extractor = _build_extractor(df)

    resultado = extractor.extraer(Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert resultado.loc[0, "SEGME"] == valor_largo[:30]


def test_extraer_agrega_fecha_inicio_y_fecha_fin_del_periodo():
    df = pd.DataFrame([_fila_excel()])
    extractor = _build_extractor(df)
    periodo = Periodo(fecha_inicio=20260827, fecha_fin=20260901)

    resultado = extractor.extraer(periodo)

    assert resultado.loc[0, "fecha_inicio"] == periodo.fecha_inicio
    assert resultado.loc[0, "fecha_fin"] == periodo.fecha_fin


def test_extraer_falla_si_faltan_columnas_esperadas():
    df = pd.DataFrame([_fila_excel()]).drop(columns=["NOMCLI"])
    extractor = _build_extractor(df)

    try:
        extractor.extraer(Periodo(fecha_inicio=20260101, fecha_fin=20260201))
        assert False, "se esperaba ExtraccionError"
    except ExtraccionError as exc:
        assert "NOMCLI" in str(exc)
