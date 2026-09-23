"""Tests de cargar_correos.cargar(): TBL_CORREO_REGISTRO se filtra por
periodo (delete + insert solo del rango), TBL_CORREO_BANDEJAS siempre se
reemplaza por completo (truncate + insert de todo, sin filtro de fecha)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from cargar_correos import _parse_fecha_utc, cargar
from mappings import ESQUEMA, TABLA_BANDEJAS, TABLA_REGISTRO
from tests.unit.fakes import FakeDatabaseGateway


def test_parse_fecha_utc_sin_offset_queda_naive():
    assert _parse_fecha_utc("2026-09-01T00:00:00") == datetime(2026, 9, 1)


def test_parse_fecha_utc_solo_fecha_inicio_es_medianoche():
    assert _parse_fecha_utc("2026-09-01") == datetime(2026, 9, 1)


def test_parse_fecha_utc_solo_fecha_fin_incluye_el_dia_completo():
    # Fin exclusivo: '2026-09-30' como fin -> 2026-10-01 00:00, asi el 30 entra entero.
    assert _parse_fecha_utc("2026-09-30", es_fin=True) == datetime(2026, 10, 1)


def test_parse_fecha_utc_fin_con_hora_no_se_desplaza():
    assert _parse_fecha_utc("2026-09-23T00:00:00", es_fin=True) == datetime(2026, 9, 23)


def test_parse_fecha_utc_con_offset_se_normaliza_a_utc_naive():
    # -05:00 (Peru/Bogota) equivale a las 05:00 UTC
    assert _parse_fecha_utc("2026-09-01T00:00:00-05:00") == datetime(2026, 9, 1, 5, 0, 0)


def _registro_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FechaHora_UTC_Texto": [
                datetime(2026, 8, 31, 23, 0, 0),  # fuera de rango (antes)
                datetime(2026, 9, 5, 12, 0, 0),  # dentro de rango
                datetime(2026, 9, 22, 0, 0, 0),  # fuera de rango (limite exclusivo)
            ],
            "ID_Mensaje": ["MSG-1", "MSG-2", "MSG-3"],
        }
    )


def _bandejas_df() -> pd.DataFrame:
    return pd.DataFrame({"Correo_Bandeja": ["SM68@movistar.cl", "SM69@movistar.cl"]})


def test_registro_se_filtra_por_periodo_delete_e_insert():
    gateway = FakeDatabaseGateway()
    fecha_inicio = datetime(2026, 9, 1)
    fecha_fin = datetime(2026, 9, 22)

    cargar(gateway, _registro_df(), _bandejas_df(), fecha_inicio, fecha_fin)

    assert len(gateway.deletes) == 1
    sql, params = gateway.deletes[0]
    assert TABLA_REGISTRO in sql
    assert params == (fecha_inicio, fecha_fin)

    insertado = gateway.inserted[TABLA_REGISTRO]
    assert list(insertado["ID_Mensaje"]) == ["MSG-2"]


def test_bandejas_siempre_se_trunca_y_reemplaza_completo():
    gateway = FakeDatabaseGateway()

    cargar(gateway, _registro_df(), _bandejas_df(), datetime(2026, 9, 1), datetime(2026, 9, 22))

    assert gateway.truncated_tables == [TABLA_BANDEJAS]
    assert len(gateway.inserted[TABLA_BANDEJAS]) == 2


def test_devuelve_conteos_de_la_operacion():
    gateway = FakeDatabaseGateway()
    gateway.filas_a_eliminar = 7

    eliminadas, insertadas_registro, insertadas_bandejas = cargar(
        gateway, _registro_df(), _bandejas_df(), datetime(2026, 9, 1), datetime(2026, 9, 22)
    )

    assert eliminadas == 7
    assert insertadas_registro == 1
    assert insertadas_bandejas == 2
