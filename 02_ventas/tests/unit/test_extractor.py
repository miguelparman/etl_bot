import pandas as pd

import extraccion.extractor as extractor
import mappings
from tests.unit.fakes import FakeDatabaseGateway, FakeSharePointCsvReader, FakeSharePointExcelReader


def test_extraer_senhalizaciones_lee_el_csv_correcto():
    esperado = pd.DataFrame({"Tu DNI": ["1"]})
    reader = FakeSharePointCsvReader({mappings.ARCHIVO_SENHALIZACIONES_CSV: esperado})
    resultado = extractor.extraer_senhalizaciones(reader)
    pd.testing.assert_frame_equal(resultado, esperado)


def test_extraer_dni_senhalizaciones_lee_la_hoja_correcta():
    esperado = pd.DataFrame({"DNI ORIGEN": ["1"]})
    reader = FakeSharePointExcelReader({(mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_DNI_SENALIZACIONES): esperado})
    resultado = extractor.extraer_dni_senhalizaciones(reader)
    pd.testing.assert_frame_equal(resultado, esperado)


def test_extraer_ventas_basev2_lee_funnel_ventas_v2():
    esperado = pd.DataFrame({"Fecha Ingreso": ["2026-01-01"]})
    reader = FakeSharePointExcelReader({(mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_BASEV2): esperado})
    resultado = extractor.extraer_ventas_basev2(reader)
    pd.testing.assert_frame_equal(resultado, esperado)


def test_extraer_ventas_rango_comisiones_lee_base_carta_meta():
    esperado = pd.DataFrame({"PERIODO": [202608]})
    reader = FakeSharePointExcelReader({(mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_COMISIONES_MES): esperado})
    resultado = extractor.extraer_ventas_rango_comisiones(reader)
    pd.testing.assert_frame_equal(resultado, esperado)


def test_extraer_ventas_basev2_temp_lee_la_tabla_correcta():
    esperado = pd.DataFrame({"Fecha Ingreso": ["2026-01-01"]})
    db = FakeDatabaseGateway()
    db.tables[mappings.TABLA_VENTAS_BASEV2_TEMP] = esperado
    resultado = extractor.extraer_ventas_basev2_temp(db)
    pd.testing.assert_frame_equal(resultado, esperado)
