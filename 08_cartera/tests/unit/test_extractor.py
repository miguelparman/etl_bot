
import pandas as pd

import mappings
from exceptions import ExtraccionError
from extraccion import extractor
from models import Periodo
from tests.unit.fakes import FakeSpreadsheetReader

_EXCEL_PATH = "05 CARTERA/CARTERA_FRACTALIA.xlsx"


def _fila_excel(**overrides) -> dict:
    fila = {col: "x" for col in mappings.EXCEL_COLUMNS}
    fila.update(overrides)
    return fila


def _reader(df_hoja1: pd.DataFrame) -> FakeSpreadsheetReader:
    return FakeSpreadsheetReader({mappings.EXCEL_SHEET: df_hoja1})


def test_extraer_devuelve_las_26_columnas_de_staging_en_orden():
    df = pd.DataFrame([_fila_excel()])

    resultado = extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert list(resultado.columns) == list(mappings.STAGING_INSERT_COLUMNS)


def test_extraer_descarta_rutcli_y_rut10():
    df = pd.DataFrame([_fila_excel()])

    resultado = extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert "RUTCLI" not in resultado.columns
    assert "RUT10" not in resultado.columns


def test_extraer_falla_si_segme_excede_su_ancho_de_truncamiento():
    # Componente 'Conversion de datos': SEGME tiene errorRowDisposition=
    # "FailComponent" en el .dtsx original -- un valor que excede el ancho
    # (30) debe abortar la extraccion, no truncarse en silencio.
    valor_largo = "S" * 100
    df = pd.DataFrame([_fila_excel(SEGME=valor_largo)])

    try:
        extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))
        assert False, "se esperaba ExtraccionError"
    except ExtraccionError as exc:
        assert "SEGME" in str(exc)


def test_extraer_trunca_segme_en_silencio_si_no_excede_el_ancho():
    valor_corto = "S" * 30
    df = pd.DataFrame([_fila_excel(SEGME=valor_corto)])

    resultado = extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert resultado.loc[0, "SEGME"] == valor_corto


def test_extraer_trunca_nomcli_en_silencio_aunque_exceda_su_ancho():
    # NOMCLI es la unica columna con errorRowDisposition="IgnoreFailure" en
    # el componente 'Conversion de datos' original: se trunca sin abortar.
    valor_largo = "N" * 200
    df = pd.DataFrame([_fila_excel(NOMCLI=valor_largo)])

    resultado = extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))

    assert resultado.loc[0, "NOMCLI"] == valor_largo[:100]


def test_extraer_agrega_fecha_inicio_y_fecha_fin_del_periodo():
    df = pd.DataFrame([_fila_excel()])
    periodo = Periodo(fecha_inicio=20260827, fecha_fin=20260901)

    resultado = extractor.extraer(_reader(df), _EXCEL_PATH, periodo)

    assert resultado.loc[0, "fecha_inicio"] == periodo.fecha_inicio
    assert resultado.loc[0, "fecha_fin"] == periodo.fecha_fin


def test_extraer_falla_si_faltan_columnas_esperadas():
    df = pd.DataFrame([_fila_excel()]).drop(columns=["NOMCLI"])

    try:
        extractor.extraer(_reader(df), _EXCEL_PATH, Periodo(fecha_inicio=20260101, fecha_fin=20260201))
        assert False, "se esperaba ExtraccionError"
    except ExtraccionError as exc:
        assert "NOMCLI" in str(exc)
