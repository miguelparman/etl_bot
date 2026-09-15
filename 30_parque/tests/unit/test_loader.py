import pandas as pd

import mappings
from carga import loader
from tests.unit.fakes import FakeDatabaseGateway


def test_truncar_tabla_usa_la_tabla_destino_del_spec():
    db = FakeDatabaseGateway()

    loader.truncar_tabla(db, mappings.FIJO_SPEC)
    loader.truncar_tabla(db, mappings.MOVIL_SPEC)

    assert db.truncated_tables == [mappings.FIJO_SPEC.tabla_destino, mappings.MOVIL_SPEC.tabla_destino]


def test_cargar_actual_delega_en_bulk_insert():
    db = FakeDatabaseGateway()
    df = pd.DataFrame([{"periodo": "202607"}])

    filas = loader.cargar_actual(db, mappings.MOVIL_SPEC, df)

    assert filas == 1
    assert mappings.MOVIL_SPEC.tabla_destino in db.inserted
    assert db.inserted[mappings.MOVIL_SPEC.tabla_destino].equals(df)


def test_borrar_historico_periodo_ejecuta_el_delete_del_spec_con_el_periodo_como_parametro():
    db = FakeDatabaseGateway()
    db.rowcount_results = [7]

    filas = loader.borrar_historico_periodo(db, mappings.FIJO_SPEC, "202607")

    assert filas == 7
    sql_ejecutado, params = db.executed_rowcount_scripts[0]
    assert sql_ejecutado == mappings.FIJO_SPEC.sql_delete_historico
    assert params == ("202607",)


def test_insertar_historico_desde_actual_arma_un_insert_select_desde_la_tabla_actual():
    db = FakeDatabaseGateway()
    db.rowcount_results = [3]

    filas = loader.insertar_historico_desde_actual(db, mappings.MOVIL_SPEC, "202607")

    assert filas == 3
    sql_ejecutado, params = db.executed_rowcount_scripts[0]
    assert params == ("202607",)
    assert f"INSERT INTO [dbo].[{mappings.MOVIL_SPEC.tabla_historico}]" in sql_ejecutado
    assert f"FROM [dbo].[{mappings.MOVIL_SPEC.tabla_destino}]" in sql_ejecutado
    assert f"WHERE [{mappings.COLUMNA_PERIODO}] = ?" in sql_ejecutado
    for columna in mappings.MOVIL_SPEC.nombres_columnas:
        assert f"[{columna}]" in sql_ejecutado
