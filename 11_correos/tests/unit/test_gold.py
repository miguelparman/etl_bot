"""Tests de gold.py: orden y parametros de la carga del modelo estrella
(dimensiones antes que hechos, calendario por anios enteros, periodo vs
completo) y la validacion posterior. El T-SQL en si se valida en vivo contra
CL_MOVIL (ver README)."""

from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd

from gold import cargar_periodo_gold, recargar_gold_completo, validar
from mappings import (
    ESQUEMA_GOLD,
    REGLAS_ASUNTO_AGRUPADO,
    TABLA_DIM_ASUNTO_AGRUPADO,
    TABLA_DIM_BANDEJA,
    TABLA_DIM_FECHA,
    TABLA_DIM_TIPO,
    TABLA_FACT_MENSAJE,
)
from tests.unit.fakes import FakeDatabaseGateway

_PERIODO = (datetime(2026, 9, 1), datetime(2026, 10, 1))


def _rango(desde: date, hasta: date) -> pd.DataFrame:
    return pd.DataFrame({"DESDE": [desde], "HASTA": [hasta]})


def _tabla_de(sql: str) -> str:
    """Tabla gold que escribe la sentencia (INSERT INTO / MERGE / DELETE FROM)."""
    encontrada = re.search(rf"(?:INSERT INTO|MERGE|DELETE FROM) \[{ESQUEMA_GOLD}\]\.\[(\w+)\]", sql)
    return encontrada.group(1) if encontrada else "?"


def test_periodo_carga_dimensiones_antes_que_hechos():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [_rango(date(2026, 9, 16), date(2026, 9, 23))]

    cargar_periodo_gold(gateway, *_PERIODO)

    tablas = [_tabla_de(sql) for sql, _ in gateway.deletes]
    assert tablas == [
        TABLA_DIM_FECHA,
        TABLA_DIM_TIPO,
        TABLA_DIM_ASUNTO_AGRUPADO,
        TABLA_DIM_BANDEJA,
        TABLA_FACT_MENSAJE,  # DELETE del periodo
        TABLA_FACT_MENSAJE,  # INSERT del periodo
    ]
    assert gateway.truncated_tables == []


def test_periodo_borra_e_inserta_hechos_del_mismo_rango():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [_rango(date(2026, 9, 16), date(2026, 9, 23))]

    cargar_periodo_gold(gateway, *_PERIODO)

    (sql_delete, params_delete), (sql_insert, params_insert) = gateway.deletes[-2:]
    assert sql_delete.startswith("DELETE") and params_delete == _PERIODO
    assert "INSERT INTO" in sql_insert and "WHERE" in sql_insert and params_insert == _PERIODO


def test_calendario_se_completa_por_anios_enteros():
    gateway = FakeDatabaseGateway()
    # Un periodo que cruza el anio (hora local) -> calendario de ambos anios completos.
    gateway.resultados_select = [_rango(date(2025, 12, 31), date(2026, 1, 2))]

    cargar_periodo_gold(gateway, datetime(2026, 1, 1), datetime(2026, 1, 3))

    _, params_fecha = gateway.deletes[0]
    assert params_fecha == (date(2025, 1, 1), date(2026, 12, 31))


def test_sin_datos_en_el_periodo_no_toca_el_calendario():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [_rango(None, None)]

    cargar_periodo_gold(gateway, *_PERIODO)

    assert TABLA_DIM_FECHA not in [_tabla_de(sql) for sql, _ in gateway.deletes]


def test_dim_asunto_recibe_todos_los_grupos_de_las_reglas():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [_rango(date(2026, 9, 16), date(2026, 9, 23))]

    cargar_periodo_gold(gateway, *_PERIODO)

    _, params = next((sql, p) for sql, p in gateway.deletes if _tabla_de(sql) == TABLA_DIM_ASUNTO_AGRUPADO)
    assert params == tuple(grupo for grupo, _, _ in REGLAS_ASUNTO_AGRUPADO)


def test_completo_trunca_solo_hechos_e_inserta_sin_filtro():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [_rango(date(2026, 9, 16), date(2026, 9, 23))]

    recargar_gold_completo(gateway)

    assert gateway.truncated_tables == [TABLA_FACT_MENSAJE]
    assert not any(sql.lstrip().startswith("DELETE") for sql, _ in gateway.deletes)
    sql_insert, params_insert = gateway.deletes[-1]
    assert "INSERT INTO" in sql_insert and "WHERE" not in sql_insert
    assert params_insert == ()


def test_validar_ok_y_no_cuadra():
    gateway = FakeDatabaseGateway()
    gateway.resultados_select = [
        pd.DataFrame({"FILAS_SILVER": [10], "FILAS_FACT": [10], "FILAS_SIN_BANDEJA_O_TIPO": [0]}),
        pd.DataFrame({"FILAS_SILVER": [10], "FILAS_FACT": [9], "FILAS_SIN_BANDEJA_O_TIPO": [0]}),
        pd.DataFrame({"FILAS_SILVER": [10], "FILAS_FACT": [10], "FILAS_SIN_BANDEJA_O_TIPO": [1]}),
    ]

    assert validar(gateway, _PERIODO) is True
    assert validar(gateway, _PERIODO) is False
    assert validar(gateway, None) is False
    assert gateway.selects[0][1] == _PERIODO * 3
    assert gateway.selects[2][1] == ()
