import pandas as pd

import mappings
from transformacion import transformer


def test_reordenar_columnas_respeta_el_orden_del_destino():
    columnas_desordenadas = list(reversed(mappings.FIJO_SPEC.nombres_columnas))
    df = pd.DataFrame([{c: "x" for c in columnas_desordenadas}])

    resultado = transformer.reordenar_columnas(df, mappings.FIJO_SPEC)

    assert list(resultado.columns) == list(mappings.FIJO_SPEC.nombres_columnas)


def test_reordenar_columnas_funciona_para_movil():
    columnas_desordenadas = list(reversed(mappings.MOVIL_SPEC.nombres_columnas))
    df = pd.DataFrame([{c: "x" for c in columnas_desordenadas}])

    resultado = transformer.reordenar_columnas(df, mappings.MOVIL_SPEC)

    assert list(resultado.columns) == list(mappings.MOVIL_SPEC.nombres_columnas)
