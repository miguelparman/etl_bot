import pandas as pd

import mappings
from extraccion import extractor
from tests.unit.fakes import FakeSharePointCsvReader


def test_extraer_descarga_el_csv_del_flujo_sin_filtrar():
    df_fijo = pd.DataFrame(
        [
            {c.nombre: "x" for c in mappings.FIJO_SPEC.columnas},
            {c.nombre: "y" for c in mappings.FIJO_SPEC.columnas},
        ]
    )
    reader = FakeSharePointCsvReader({mappings.FIJO_SPEC.archivo_csv: df_fijo})

    resultado = extractor.extraer(reader, mappings.FIJO_SPEC)

    assert resultado.equals(df_fijo)


def test_extraer_usa_el_archivo_csv_declarado_en_el_spec():
    df_movil = pd.DataFrame([{c.nombre: "z" for c in mappings.MOVIL_SPEC.columnas}])
    reader = FakeSharePointCsvReader({mappings.MOVIL_SPEC.archivo_csv: df_movil})

    resultado = extractor.extraer(reader, mappings.MOVIL_SPEC)

    assert resultado.equals(df_movil)
