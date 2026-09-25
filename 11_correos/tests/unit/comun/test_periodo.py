"""Tests de comun/periodo.py: interpretacion de FECHA_INICIO/FECHA_FIN (solo
fecha = dia completo, con hora = fin exclusivo, offset -> UTC) y validacion
del rango."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from comun.exceptions import PeriodoError
from comun.periodo import ahora_local, parse_fecha_utc, periodo_automatico, resolver_periodo


def test_parse_fecha_utc_sin_offset_queda_naive():
    assert parse_fecha_utc("2026-09-01T00:00:00") == datetime(2026, 9, 1)


def test_parse_fecha_utc_solo_fecha_inicio_es_medianoche():
    assert parse_fecha_utc("2026-09-01") == datetime(2026, 9, 1)


def test_parse_fecha_utc_solo_fecha_fin_incluye_el_dia_completo():
    # Fin exclusivo: '2026-09-30' como fin -> 2026-10-01 00:00, asi el 30 entra entero.
    assert parse_fecha_utc("2026-09-30", es_fin=True) == datetime(2026, 10, 1)


def test_parse_fecha_utc_fin_con_hora_no_se_desplaza():
    assert parse_fecha_utc("2026-09-23T00:00:00", es_fin=True) == datetime(2026, 9, 23)


def test_parse_fecha_utc_con_offset_se_normaliza_a_utc_naive():
    # -05:00 (Peru/Bogota) equivale a las 05:00 UTC
    assert parse_fecha_utc("2026-09-01T00:00:00-05:00") == datetime(2026, 9, 1, 5, 0, 0)


def test_ahora_local_es_utc_menos_5_naive_y_al_segundo():
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    local = ahora_local()
    assert local.tzinfo is None and local.microsecond == 0
    assert abs((utc - local) - timedelta(hours=5)) < timedelta(seconds=5)


def test_resolver_periodo_ok():
    assert resolver_periodo("2026-09-01", "2026-09-30") == (datetime(2026, 9, 1), datetime(2026, 10, 1))


@pytest.mark.parametrize(
    ("inicio", "fin", "mensaje"),
    [
        (None, "2026-09-30", "Periodo incompleto"),
        ("2026-09-01", "", "Periodo incompleto"),
        ("no-es-fecha", "2026-09-30", "Fecha invalida"),
        ("2026-09-30T00:00:00", "2026-09-01T00:00:00", "posterior"),
    ],
)
def test_resolver_periodo_invalido(inicio, fin, mensaje):
    with pytest.raises(PeriodoError, match=mensaje):
        resolver_periodo(inicio, fin)


@pytest.mark.parametrize(
    ("hoy", "esperado"),
    [
        # Primeros 7 dias: mes anterior + mes en curso.
        (date(2026, 9, 1), (datetime(2026, 8, 1), datetime(2026, 10, 1))),
        (date(2026, 9, 7), (datetime(2026, 8, 1), datetime(2026, 10, 1))),
        # Desde el dia 8: solo el mes en curso.
        (date(2026, 9, 8), (datetime(2026, 9, 1), datetime(2026, 10, 1))),
        (date(2026, 9, 30), (datetime(2026, 9, 1), datetime(2026, 10, 1))),
        # Cruce de anio.
        (date(2027, 1, 5), (datetime(2026, 12, 1), datetime(2027, 2, 1))),
        (date(2026, 12, 15), (datetime(2026, 12, 1), datetime(2027, 1, 1))),
    ],
)
def test_periodo_automatico(hoy, esperado):
    assert periodo_automatico(hoy) == esperado


@pytest.mark.parametrize(("inicio", "fin"), [(None, None), ("", "")])
def test_resolver_periodo_sin_fechas_es_automatico(inicio, fin):
    assert resolver_periodo(inicio, fin, hoy=date(2026, 9, 7)) == (datetime(2026, 8, 1), datetime(2026, 10, 1))


def test_resolver_periodo_sin_fechas_usa_la_fecha_local_por_defecto():
    assert resolver_periodo(None, None) == periodo_automatico(ahora_local().date())


def test_resolver_periodo_manual_ignora_hoy():
    assert resolver_periodo("2026-09-01", "2026-09-30", hoy=date(2026, 12, 3)) == (
        datetime(2026, 9, 1),
        datetime(2026, 10, 1),
    )
