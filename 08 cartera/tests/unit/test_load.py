import pandas as pd

from app.application import load, mappings
from tests.unit.fakes import FakeDatabaseGateway


def _staging_df_completo() -> pd.DataFrame:
    """Simula TBL_CARTERA con las columnas de ACTUAL_SOURCE_COLUMNS mas
    columnas de staging que 'ALIMENTA TABLA' no copia (fecha_inicio, STATUS),
    para probar que se descartan."""
    columnas = list(mappings.ACTUAL_SOURCE_COLUMNS) + ["fecha_inicio", "STATUS"]
    fila = {col: f"valor_{col}" for col in columnas}
    return pd.DataFrame([fila])


def test_copiar_temporal_a_actual_selecciona_y_renombra_columnas():
    db_temporales = FakeDatabaseGateway()
    db_temporales.tables[mappings.TABLA_STAGING] = _staging_df_completo()
    db_cartera = FakeDatabaseGateway()

    filas = load.copiar_temporal_a_actual(db_temporales, db_cartera)

    assert filas == 1
    df_insertado = db_cartera.inserted[mappings.TABLA_ACTUAL]
    assert set(df_insertado.columns) == set(mappings.ACTUAL_COLUMN_RENAME.values())
    assert "fecha_inicio" not in df_insertado.columns
    assert "STATUS" not in df_insertado.columns
    assert df_insertado.loc[0, "RUT"] == "valor_RUT_DV"
    assert df_insertado.loc[0, "COD_DNI"] == "valor_DNI"


def test_truncar_staging_y_truncar_actual_usan_la_tabla_correcta():
    db_temporales = FakeDatabaseGateway()
    db_cartera = FakeDatabaseGateway()

    load.truncar_staging(db_temporales)
    load.truncar_actual(db_cartera)

    assert db_temporales.truncated_tables == [mappings.TABLA_STAGING]
    assert db_cartera.truncated_tables == [mappings.TABLA_ACTUAL]


def test_cargar_staging_delega_en_bulk_insert():
    db_temporales = FakeDatabaseGateway()
    df = pd.DataFrame([{"RUT_DV": "1"}])

    filas = load.cargar_staging(db_temporales, df)

    assert filas == 1
    assert mappings.TABLA_STAGING in db_temporales.inserted
