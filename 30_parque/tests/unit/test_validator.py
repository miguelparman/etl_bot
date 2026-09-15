import pandas as pd
import pytest

import mappings
from exceptions import ValidacionError
from validacion import validator


def _fila_fijo(**overrides) -> dict:
    fila = {c.nombre: "x" for c in mappings.FIJO_SPEC.columnas}
    fila["periodo"] = "202607"
    fila.update(overrides)
    return fila


def _fila_movil(**overrides) -> dict:
    fila = {c.nombre: "x" for c in mappings.MOVIL_SPEC.columnas}
    fila["periodo"] = "202607"
    fila.update(overrides)
    return fila


def test_validar_columnas_falla_si_falta_una_columna_esperada():
    df = pd.DataFrame([_fila_fijo()]).drop(columns=["rutcli"])
    with pytest.raises(ValidacionError):
        validator.validar_columnas(df, mappings.FIJO_SPEC)


def test_validar_columnas_no_falla_si_estan_todas():
    df = pd.DataFrame([_fila_fijo()])
    validator.validar_columnas(df, mappings.FIJO_SPEC)  # no debe lanzar


def test_filtrar_periodo_descarta_filas_de_otros_periodos():
    df = pd.DataFrame([_fila_fijo(periodo="202607"), _fila_fijo(periodo="202608")])

    filtrado = validator.filtrar_periodo(df, mappings.FIJO_SPEC, "202607")

    assert len(filtrado) == 1
    assert filtrado.iloc[0]["periodo"] == "202607"


def test_validar_longitudes_falla_si_una_columna_excede_el_ancho():
    df = pd.DataFrame([_fila_fijo(rutcli="x" * 51)])  # rutcli maximo 50 en FIJO
    with pytest.raises(ValidacionError):
        validator.validar_longitudes(df, mappings.FIJO_SPEC)


def test_validar_longitudes_distingue_rutcli_entre_fijo_y_movil():
    # 'rutcli' tiene largo maximo 10 en MOVIL vs 50 en FIJO (preservado tal
    # cual del .dtsx original): el mismo valor de 11 caracteres debe pasar en
    # FIJO pero fallar en MOVIL.
    valor = "x" * 11
    df_fijo = pd.DataFrame([_fila_fijo(rutcli=valor)])
    df_movil = pd.DataFrame([_fila_movil(rutcli=valor)])

    validator.validar_longitudes(df_fijo, mappings.FIJO_SPEC)  # no debe lanzar

    with pytest.raises(ValidacionError):
        validator.validar_longitudes(df_movil, mappings.MOVIL_SPEC)


def test_validar_corre_columnas_filtro_y_longitudes_en_ese_orden():
    # La fila que excede el largo maximo es de OTRO periodo: al filtrar
    # primero por periodo, esa fila se descarta antes de validar longitudes
    # (igual que en SSIS, donde el filtro SQL corria antes de que el Data
    # Flow viera las filas).
    df = pd.DataFrame(
        [
            _fila_fijo(periodo="202607"),
            _fila_fijo(periodo="202608", rutcli="x" * 51),
        ]
    )

    resultado = validator.validar(df, mappings.FIJO_SPEC, "202607")

    assert len(resultado) == 1
    assert resultado.iloc[0]["periodo"] == "202607"


def test_validar_lanza_si_la_fila_del_periodo_solicitado_excede_el_largo():
    df = pd.DataFrame([_fila_fijo(periodo="202607", rutcli="x" * 51)])
    with pytest.raises(ValidacionError):
        validator.validar(df, mappings.FIJO_SPEC, "202607")
