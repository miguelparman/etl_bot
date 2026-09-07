import pandas as pd

from contactos.columns import COLUMNAS_ORIGEN, MAPEO_DESTINO
from contactos.transformer import transform_contactos
from contactos.validator import validar_contactos


def _fila_valida(**overrides) -> dict:
    fila = {
        "No  identificación fiscal": "760596132",
        "Nombre del cliente": "REIFENHAUSER LATINA SPA",
        "Segmento Global": "(TGS) Negocios",
        "Subsegmento local": "Medianas Empresas",
        "Número de documento": "141438905",
        "Nombre": "Jaime",
        "Apellidos": "Medina",
        "Cargo": "técnico",
        "Teléfono": "222222222",
        "Móvil": "961402226",
        "Correo electrónico": "jaime.medina@example.com",
        "Autorizaciones funcionales": "",
        "Acceso a Portal Platino": "1",
        "Representante legal": "0",
        "Fecha de creación": "04-12-2017",
        "Fecha de la última modificación": "10-01-2025",
        "Creado por": "David Gonzalez",
        "Última modificación por": "Salvador Arribas",
        "Id  de contacto": "0031r000020g2gK",
    }
    fila.update(overrides)
    return fila


def _df(*filas) -> pd.DataFrame:
    return pd.DataFrame(list(filas), columns=COLUMNAS_ORIGEN)


def test_transform_renombra_a_columnas_destino():
    df = transform_contactos(_df(_fila_valida()))
    assert set(MAPEO_DESTINO.values()) == set(df.columns)


def test_transform_castea_enteros_desde_texto_bool():
    df = transform_contactos(_df(_fila_valida(**{"Acceso a Portal Platino": "True", "Representante legal": "False"})))
    assert df.loc[0, "ACCESO PLATINO"] == 1
    assert df.loc[0, "REPRESENTANTE LEGAL"] == 0


def test_transform_parsea_fechas_dia_primero():
    df = transform_contactos(_df(_fila_valida()))
    assert str(df.loc[0, "FECHA CREACIÓN"]) == "2017-12-04"


def test_transform_no_convierte_nan_en_texto_nan():
    # El extractor ya convierte "" -> NaN vía na_values=[""] al leer el CSV;
    # acá se simula esa entrada (None) para blindar que el transformer no
    # use astype(str) -- eso convertiría el NaN real en el string "nan".
    df = transform_contactos(_df(_fila_valida(**{"Autorizaciones funcionales": None})))
    assert pd.isna(df.loc[0, "AUTORIZACIONES FUNCIONALES"])


def test_validar_rechaza_columna_entera_no_numerica():
    df = _df(_fila_valida(**{"Acceso a Portal Platino": "no-es-numero"}))
    try:
        validar_contactos(df)
        assert False, "debía lanzar ValueError"
    except ValueError as exc:
        assert "Acceso a Portal Platino" in str(exc)


def test_validar_ok_con_fila_valida():
    validar_contactos(_df(_fila_valida()))


def test_transform_trunca_telefono_silenciosamente():
    # IgnoreFailure en el .dtsx: se trunca a 20 caracteres, no se rechaza la fila.
    df = transform_contactos(_df(_fila_valida(**{"Teléfono": "Nelson: 56 9 53068855"})))
    assert df.loc[0, "TELÉFONO"] == "Nelson: 56 9 5306885"
    assert len(df.loc[0, "TELÉFONO"]) == 20


def test_validar_rechaza_columna_fail_component_muy_larga():
    # "Correo electrónico" es FailComponent (a diferencia de Teléfono): debe
    # rechazar el archivo entero en vez de truncar en silencio.
    df = _df(_fila_valida(**{"Correo electrónico": "a" * 81 + "@example.com"}))
    try:
        validar_contactos(df)
        assert False, "debía lanzar ValueError"
    except ValueError as exc:
        assert "Correo electrónico" in str(exc)
