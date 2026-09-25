
import pandas as pd
import pytest

import mappings
import sql
from exceptions import PipelineError, ValidacionError
from models import Periodo
from pipeline import CarteraPipeline
from tests.unit.fakes import FakeDatabaseGateway, FakeSpreadsheetReader


def _fila_excel(**overrides) -> dict:
    fila = {col: "x" for col in mappings.EXCEL_COLUMNS}
    fila.update(overrides)
    return fila


def _build_pipeline():
    db_cartera = FakeDatabaseGateway()
    db_temporales = FakeDatabaseGateway()
    reader = FakeSpreadsheetReader({mappings.EXCEL_SHEET: pd.DataFrame([_fila_excel()])})

    pipeline = CarteraPipeline(
        db_cartera=db_cartera,
        db_temporales=db_temporales,
        spreadsheet_reader=reader,
        excel_path="05 CARTERA/CARTERA_FRACTALIA.xlsx",
    )
    return pipeline, db_cartera, db_temporales


def test_pipeline_ejecuta_las_3_sequences_en_orden_y_carga_las_tablas_esperadas():
    pipeline, db_cartera, db_temporales = _build_pipeline()
    # Data Flow 2 ('ALIMENTA TABLA') lee la staging ya cargada: se simula el
    # resultado esperado tras 'CARGA DNI' (columnas de ACTUAL_SOURCE_COLUMNS).
    db_temporales.tables[mappings.TABLA_STAGING] = pd.DataFrame(
        [{col: "x" for col in mappings.ACTUAL_SOURCE_COLUMNS}]
    )
    periodo = Periodo(fecha_inicio=20260827, fecha_fin=20260901)

    resultado = pipeline.run(periodo)

    # CARGA CARTERA TEMPORAL
    assert db_temporales.truncated_tables == [mappings.TABLA_STAGING]
    assert mappings.TABLA_STAGING in db_temporales.inserted
    assert any(s == sql.ENRIQUECER_CON_ASESORES for s, _ in db_temporales.executed_scripts)
    assert any(s == sql.NORMALIZAR_SUB_SEGMENTO for s, _ in db_temporales.executed_scripts)

    # CARGA CARTERA ACTUAL
    assert db_cartera.truncated_tables[0] == mappings.TABLA_ACTUAL
    assert mappings.TABLA_ACTUAL in db_cartera.inserted

    # HISTORICO CARTERA: el orden real del Sequence Container es
    # ACTUALIZA STATUS -> LIMITA CLIENTES -> LIMPIA TEMPORAL -> CARGA (la
    # tarea CARGA corre despues de que LIMPIA TEMPORAL vacia la staging).
    # Se verifica el orden exacto, no solo la presencia, para proteger contra
    # una regresion que reordene los pasos en pipeline.py.
    scripts_cartera = [s for s, _ in db_cartera.executed_scripts]
    assert scripts_cartera == [
        sql.ACTUALIZA_STATUS_TEMP_CARTERA,
        sql.LIMITA_CLIENTES,
        sql.LIMPIA_TEMPORAL,
        sql.CARGA_HISTORICO,
    ]

    # LIMITA CLIENTES debe recibir fecha_inicio del periodo como parametro.
    limita_params = next(p for s, p in db_cartera.executed_scripts if s == sql.LIMITA_CLIENTES)
    assert limita_params == (periodo.fecha_inicio,)

    assert resultado.periodo == periodo
    assert resultado.filas_extraidas == 1


def test_pipeline_aborta_si_la_validacion_falla_y_no_continua_con_cartera_actual():
    pipeline, db_cartera, db_temporales = _build_pipeline()
    db_temporales.scalars[sql.VALIDA_ASESOR_NO_ASIGNADO] = 1  # fuerza el fallo de VALIDA

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run(Periodo(fecha_inicio=20260827, fecha_fin=20260901))

    assert isinstance(exc_info.value.causa, ValidacionError)
    # No debe haber avanzado a 'CARGA CARTERA ACTUAL'.
    assert db_cartera.truncated_tables == []
    assert db_cartera.inserted == {}
