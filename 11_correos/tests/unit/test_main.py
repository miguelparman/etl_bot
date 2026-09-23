"""Tests de main.py (punto de entrada unico): seleccion de etapas con
--desde/--solo, cuando hace falta el periodo, y restricciones de --completo."""

from __future__ import annotations

import pytest

import main


@pytest.mark.parametrize(
    ("argv", "esperado"),
    [
        ([], ["ingesta", "bronze", "silver", "gold"]),
        (["--desde", "silver"], ["silver", "gold"]),
        (["--desde", "gold"], ["gold"]),
        (["--solo", "bronze"], ["bronze"]),
        (["--solo", "ingesta"], ["ingesta"]),
    ],
)
def test_seleccion_de_etapas(argv, esperado):
    assert main.parse_args(argv).etapas == esperado


@pytest.mark.parametrize("argv", [["--completo"], ["--solo", "bronze", "--completo"], ["--desde", "bronze", "--completo"]])
def test_completo_no_aplica_a_ingesta_ni_bronze(argv):
    with pytest.raises(SystemExit):
        main.parse_args(argv)


@pytest.mark.parametrize("argv", [["--solo", "silver", "--completo"], ["--desde", "silver", "--completo"]])
def test_completo_permitido_en_silver_y_gold(argv):
    assert main.parse_args(argv).completo


def test_desde_y_solo_son_excluyentes():
    with pytest.raises(SystemExit):
        main.parse_args(["--desde", "silver", "--solo", "gold"])


@pytest.mark.parametrize(
    ("etapas", "completo", "necesita"),
    [
        (["ingesta"], False, False),  # la copia no usa periodo
        (["ingesta", "bronze", "silver", "gold"], False, True),
        (["silver", "gold"], True, False),  # completo: sin filtro de periodo
        (["gold"], False, True),
    ],
)
def test_necesita_periodo(etapas, completo, necesita):
    assert main._necesita_periodo(etapas, completo) is necesita
