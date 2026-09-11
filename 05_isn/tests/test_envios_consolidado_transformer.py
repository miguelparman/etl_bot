import pandas as pd
import pytest

from isn.columns import COLUMNAS_ENVIOS_CONSOLIDADO
from isn.transformers.envios_consolidado import transform_envios_consolidado
from isn.validators.envios_validator import validar_envios_consolidado


def _fila_valida(**overrides) -> dict:
    fila = {c: "valor" for c in COLUMNAS_ENVIOS_CONSOLIDADO}
    fila["FECHA_EVENTO"] = "20260904"
    fila["Número del caso"] = "15925857"
    fila.update(overrides)
    return fila


def _df(*filas) -> pd.DataFrame:
    return pd.DataFrame(list(filas), columns=COLUMNAS_ENVIOS_CONSOLIDADO)


def test_transform_castea_fecha_evento_y_numero_caso_a_entero():
    df = transform_envios_consolidado(_df(_fila_valida()))
    assert df.loc[0, "FECHA_EVENTO"] == 20260904
    assert df.loc[0, "Número del caso"] == 15925857
    assert str(df["FECHA_EVENTO"].dtype) == "Int64"


def test_validar_rechaza_fecha_evento_no_entera():
    df = _df(_fila_valida(FECHA_EVENTO="no-es-fecha"))
    with pytest.raises(ValueError, match="FECHA_EVENTO"):
        validar_envios_consolidado(df)


def test_validar_ok_con_fila_valida():
    validar_envios_consolidado(_df(_fila_valida()))
