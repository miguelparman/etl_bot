import pandas as pd
import pytest

import mappings
import validacion.validator as validator
from exceptions import ValidacionError
from models import ColumnaSpec


def test_validar_columnas_presentes_ok():
    df = pd.DataFrame({"A": [1], "B": [2]})
    validator.validar_columnas_presentes(df, ("A", "B"), "origen")


def test_validar_columnas_presentes_falta_columna():
    df = pd.DataFrame({"A": [1]})
    with pytest.raises(ValidacionError):
        validator.validar_columnas_presentes(df, ("A", "B"), "origen")


def test_validar_columnas_senhalizaciones_usa_solo_las_35_mapeadas():
    columnas_csv = {origen for origen, _destino in mappings.MAPEO_SENHALIZACIONES}
    df = pd.DataFrame({c: ["x"] for c in columnas_csv})
    validator.validar_columnas_senhalizaciones(df)  # no debe levantar


def test_validar_longitudes_levanta_error_si_excede_ancho_y_es_estricto():
    columnas = (ColumnaSpec("COL", 5, estricto=True),)
    df = pd.DataFrame({"COL": ["123456"]})
    with pytest.raises(ValidacionError):
        validator.validar_longitudes(df, columnas, "TABLA_TEST")


def test_validar_longitudes_no_levanta_si_no_es_estricto():
    columnas = (ColumnaSpec("COL", 5, estricto=False),)
    df = pd.DataFrame({"COL": ["123456"]})
    validator.validar_longitudes(df, columnas, "TABLA_TEST")  # no debe levantar


def test_validar_longitudes_ignora_columnas_numericas_y_fecha():
    columnas = (
        ColumnaSpec("NUM", estricto=True, tipo="numero"),
        ColumnaSpec("FECHA", estricto=True, tipo="fecha"),
    )
    df = pd.DataFrame({"NUM": ["no es numero"], "FECHA": ["no es fecha"]})
    validator.validar_longitudes(df, columnas, "TABLA_TEST")  # longitud_max=0 -> se salta


def test_validar_longitudes_senhalizaciones_dni_todas_estrictas():
    df = pd.DataFrame({"DNI ORIGEN": ["x" * 16], "DNI A CAMBIAR": ["1"], "Observación": ["obs"]})
    with pytest.raises(ValidacionError):
        validator.validar_longitudes_dni_senhalizaciones(df)
