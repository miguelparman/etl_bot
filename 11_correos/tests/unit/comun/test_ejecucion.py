"""Tests de comun/ejecucion.py: apertura y cierre de la fila del log de
ejecuciones (dbo.TBL_CORREO_LOG_EJECUCION)."""

from __future__ import annotations

from datetime import datetime

from comun.ejecucion import (
    ESTADO_EN_CURSO,
    ESTADO_ERROR,
    ESTADO_OK,
    TABLA_LOG,
    Ejecucion,
    ResultadoEjecucion,
    finalizar_ejecucion,
    iniciar_ejecucion,
)
from comun.exceptions import CargaError
from tests.unit.fakes import FakeDatabaseGateway

_PERIODO = (datetime(2026, 9, 1), datetime(2026, 10, 1))


def test_iniciar_abre_fila_en_curso_y_devuelve_id():
    gateway = FakeDatabaseGateway()
    gateway.siguiente_id = 42

    ejecucion = iniciar_ejecucion(gateway, ["ingesta", "bronze", "silver", "gold"], False, _PERIODO)

    assert ejecucion.id_ejecucion == 42
    sql, params = gateway.inserts_con_id[0]
    assert TABLA_LOG in sql and "OUTPUT INSERTED.ID_EJECUCION" in sql
    fecha_inicio, estado, etapas, modo, periodo_inicio, periodo_fin, _usuario, _equipo = params
    assert fecha_inicio == ejecucion.fecha_carga  # FECHA_CARGA = inicio de la corrida
    assert estado == ESTADO_EN_CURSO
    assert etapas == "ingesta -> bronze -> silver -> gold"
    assert modo == "periodo"
    assert (periodo_inicio, periodo_fin) == _PERIODO


def test_iniciar_en_modo_completo_sin_periodo():
    gateway = FakeDatabaseGateway()

    iniciar_ejecucion(gateway, ["silver", "gold"], True, None)

    _, params = gateway.inserts_con_id[0]
    assert params[3] == "completo"
    assert params[4] is None and params[5] is None


def test_finalizar_actualiza_estado_y_filas():
    gateway = FakeDatabaseGateway()
    ejecucion = Ejecucion(id_ejecucion=7, fecha_carga=datetime(2026, 9, 24, 7, 0, 0))
    resultado = ResultadoEjecucion(filas_bronze=10, filas_silver=10, filas_gold=10, validacion_gold="OK")

    finalizar_ejecucion(gateway, ejecucion, ESTADO_OK, resultado)

    sql, params = gateway.deletes[0]
    assert sql.lstrip().startswith("UPDATE") and TABLA_LOG in sql
    _fecha_fin, estado, bronze, silver, gold, validacion, mensaje, id_ejecucion = params
    assert (estado, bronze, silver, gold, validacion, mensaje, id_ejecucion) == (ESTADO_OK, 10, 10, 10, "OK", None, 7)


def test_finalizar_no_levanta_si_el_log_falla():
    # Si el log no se puede cerrar (ej. se cayo la conexion), no debe tapar
    # el error original de la corrida.
    gateway = FakeDatabaseGateway()
    gateway.fallar_execute = CargaError("conexion perdida")
    ejecucion = Ejecucion(id_ejecucion=7, fecha_carga=datetime(2026, 9, 24))

    finalizar_ejecucion(gateway, ejecucion, ESTADO_ERROR, ResultadoEjecucion(), "boom")
