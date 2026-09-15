import pandas as pd
import pytest

import mappings
from exceptions import PipelineError, ValidacionError
from models import ParqueFlowSpec
from pipeline import ParquePipeline
from tests.unit.fakes import FakeDatabaseGateway, FakeSharePointCsvReader


def _fila(spec: ParqueFlowSpec, **overrides) -> dict:
    fila = {c.nombre: "x" for c in spec.columnas}
    fila["periodo"] = "202607"
    fila.update(overrides)
    return fila


def _build_pipeline(fijo_rows: list[dict], movil_rows: list[dict], rowcount_results: list[int] | None = None):
    db = FakeDatabaseGateway()
    if rowcount_results is not None:
        db.rowcount_results = list(rowcount_results)
    reader = FakeSharePointCsvReader(
        {
            mappings.FIJO_SPEC.archivo_csv: pd.DataFrame(fijo_rows),
            mappings.MOVIL_SPEC.archivo_csv: pd.DataFrame(movil_rows),
        }
    )
    pipeline = ParquePipeline(
        db=db,
        sharepoint_reader=reader,
        fijo_spec=mappings.FIJO_SPEC,
        movil_spec=mappings.MOVIL_SPEC,
    )
    return pipeline, db


def test_pipeline_trunca_y_carga_ambas_tablas_actual_filtrando_por_periodo():
    fijo_rows = [_fila(mappings.FIJO_SPEC, periodo="202607"), _fila(mappings.FIJO_SPEC, periodo="202608")]
    movil_rows = [_fila(mappings.MOVIL_SPEC, periodo="202607")]
    pipeline, db = _build_pipeline(fijo_rows, movil_rows, rowcount_results=[5, 5, 3, 3])

    resultado = pipeline.run("202607")

    assert set(db.truncated_tables) == {mappings.FIJO_SPEC.tabla_destino, mappings.MOVIL_SPEC.tabla_destino}
    # Solo la fila del periodo solicitado se carga (el CSV traia 2 periodos mezclados en FIJO).
    assert len(db.inserted[mappings.FIJO_SPEC.tabla_destino]) == 1
    assert len(db.inserted[mappings.MOVIL_SPEC.tabla_destino]) == 1

    assert resultado.periodo == "202607"
    assert resultado.fijo.actual.filas_csv == 2
    assert resultado.fijo.actual.filas_periodo == 1
    assert resultado.fijo.actual.filas_cargadas == 1
    assert resultado.movil.actual.filas_cargadas == 1


def test_pipeline_ejecuta_historico_despues_de_actual_leyendo_desde_actual():
    fijo_rows = [_fila(mappings.FIJO_SPEC, periodo="202607")]
    movil_rows = [_fila(mappings.MOVIL_SPEC, periodo="202607")]
    pipeline, db = _build_pipeline(fijo_rows, movil_rows, rowcount_results=[9, 4, 2, 1])

    resultado = pipeline.run("202607")

    # DELETE + INSERT de HISTORICO se ejecutaron para ambas ramas, despues de
    # que _ACTUAL ya estaba truncada y cargada (mismo orden: TRUNCATE -> ...
    # -> Destino _ACTUAL -> DELETE -> INSERT _HISTORICO).
    assert len(db.executed_rowcount_scripts) == 4
    delete_fijo_sql, delete_fijo_params = db.executed_rowcount_scripts[0]
    assert delete_fijo_sql == mappings.FIJO_SPEC.sql_delete_historico
    assert delete_fijo_params == ("202607",)
    insert_fijo_sql, _ = db.executed_rowcount_scripts[1]
    assert f"[dbo].[{mappings.FIJO_SPEC.tabla_historico}]" in insert_fijo_sql
    assert f"[dbo].[{mappings.FIJO_SPEC.tabla_destino}]" in insert_fijo_sql

    assert resultado.fijo.historico.filas_purgadas == 9
    assert resultado.fijo.historico.filas_insertadas == 4
    assert resultado.movil.historico.filas_purgadas == 2
    assert resultado.movil.historico.filas_insertadas == 1


def test_pipeline_no_corre_historico_si_actual_falla_por_ser_dependiente():
    # 'rutcli' excede el largo maximo de FIJO (50): la sub-rama 'PQ FIJO I'
    # (_ACTUAL) debe fallar, y 'PQ FIJO II' (_HISTORICO) NO debe intentarse
    # -- igual que en el .dtsx original, donde 'PQ FIJO II' depende ("On
    # Success") de que 'PQ FIJO I' termine sin error.
    fijo_rows = [_fila(mappings.FIJO_SPEC, periodo="202607", rutcli="x" * 51)]
    movil_rows = [_fila(mappings.MOVIL_SPEC, periodo="202607")]
    pipeline, db = _build_pipeline(fijo_rows, movil_rows, rowcount_results=[2, 1])

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run("202607")

    assert isinstance(exc_info.value.causa, ValidacionError)
    # MOVIL corrio completo (ACTUAL + HISTORICO): 2 llamadas rowcount (DELETE, INSERT).
    assert len(db.executed_rowcount_scripts) == 2
    delete_movil_sql, _ = db.executed_rowcount_scripts[0]
    assert delete_movil_sql == mappings.MOVIL_SPEC.sql_delete_historico


def test_pipeline_ejecuta_movil_completo_aunque_fijo_falle_por_ser_ramas_independientes():
    fijo_rows = [_fila(mappings.FIJO_SPEC, periodo="202607", rutcli="x" * 51)]
    movil_rows = [_fila(mappings.MOVIL_SPEC, periodo="202607")]
    pipeline, db = _build_pipeline(fijo_rows, movil_rows, rowcount_results=[6, 6])

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run("202607")

    assert isinstance(exc_info.value.causa, ValidacionError)
    # FIJO: se trunca (tarea separada e incondicional) pero queda vacia porque
    # la validacion fallo despues -- igual que en el .dtsx original.
    assert mappings.FIJO_SPEC.tabla_destino in db.truncated_tables
    assert mappings.FIJO_SPEC.tabla_destino not in db.inserted
    # MOVIL: no depende de FIJO, se trunca, carga ACTUAL y corre HISTORICO igual.
    assert mappings.MOVIL_SPEC.tabla_destino in db.truncated_tables
    assert mappings.MOVIL_SPEC.tabla_destino in db.inserted
    assert len(db.executed_rowcount_scripts) == 2  # DELETE + INSERT de HISTORICO para MOVIL


def test_pipeline_reporta_el_error_de_fijo_si_fallan_ambas_ramas():
    fijo_rows = [_fila(mappings.FIJO_SPEC, periodo="202607", rutcli="x" * 51)]
    movil_rows = [_fila(mappings.MOVIL_SPEC, periodo="202607", rutcli="x" * 11)]  # movil maximo 10
    pipeline, _ = _build_pipeline(fijo_rows, movil_rows)

    with pytest.raises(PipelineError) as exc_info:
        pipeline.run("202607")

    assert "PQ FIJO I" in str(exc_info.value)
