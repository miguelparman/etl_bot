import pandas as pd

import carga.loader as loader
import mappings
import sql
from tests.unit.fakes import FakeDatabaseGateway


def test_truncar_senhalizaciones_ejecuta_el_truncate_correcto():
    db = FakeDatabaseGateway()
    loader.truncar_senhalizaciones(db)
    assert db.executed_scripts == [(sql.SQL_TRUNCATE_SENHALIZACIONES, ())]


def test_cargar_senhalizaciones_inserta_en_la_tabla_correcta():
    db = FakeDatabaseGateway()
    df = pd.DataFrame({"TU DNI": ["1"]})
    filas = loader.cargar_senhalizaciones(db, df)
    assert filas == 1
    assert db.inserted[mappings.TABLA_SENHALIZACIONES] is df


def test_truncar_ventas_basev2_ejecuta_el_truncate_correcto():
    db = FakeDatabaseGateway()
    loader.truncar_ventas_basev2(db)
    assert db.executed_scripts == [(sql.SQL_TRUNCATE_VENTAS_BASEV2_TEMP, ())]


def test_cargar_ventas_temp_inserta_en_la_tabla_correcta():
    db = FakeDatabaseGateway()
    df = pd.DataFrame({"PUSHER": ["p"]})
    loader.cargar_ventas_temp(db, df)
    assert db.inserted[mappings.TABLA_VENTAS_TEMP] is df


def test_truncar_ventas_dni_senhalizaciones_reutiliza_el_mismo_truncate_que_senhalizaciones():
    db = FakeDatabaseGateway()
    loader.truncar_ventas_dni_senhalizaciones(db)
    assert db.executed_scripts == [(sql.SQL_TRUNCATE_SENHALIZACIONES_DNI, ())]
