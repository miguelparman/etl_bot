import pytest

import sql
from exceptions import ValidacionError
from tests.unit.fakes import FakeDatabaseGateway
from validacion.validator import validar_cartera_temporal


def test_validar_no_falla_si_los_4_controles_pasan():
    db = FakeDatabaseGateway()
    validar_cartera_temporal(db)  # no debe lanzar nada


def test_validar_falla_por_rut_duplicado():
    db = FakeDatabaseGateway()
    db.scalars[sql.VALIDA_RUT_DUPLICADO] = 2

    with pytest.raises(ValidacionError, match=sql.MSG_RUT_DUPLICADO):
        validar_cartera_temporal(db)


def test_validar_falla_por_asesor_no_asignado():
    db = FakeDatabaseGateway()
    db.scalars[sql.VALIDA_ASESOR_NO_ASIGNADO] = 1

    with pytest.raises(ValidacionError, match=sql.MSG_ASESOR_NO_ASIGNADO):
        validar_cartera_temporal(db)


def test_validar_falla_por_rut_no_asignado():
    db = FakeDatabaseGateway()
    db.scalars[sql.VALIDA_RUT_NO_ASIGNADO] = 1

    with pytest.raises(ValidacionError, match=sql.MSG_RUT_NO_ASIGNADO):
        validar_cartera_temporal(db)


def test_validar_falla_por_nombre_no_asignado():
    db = FakeDatabaseGateway()
    db.scalars[sql.VALIDA_NOMBRE_NO_ASIGNADO] = 1

    with pytest.raises(ValidacionError, match=sql.MSG_NOMBRE_NO_ASIGNADO):
        validar_cartera_temporal(db)


def test_validar_se_detiene_en_el_primer_control_que_falla():
    db = FakeDatabaseGateway()
    db.scalars[sql.VALIDA_RUT_DUPLICADO] = 1
    db.scalars[sql.VALIDA_ASESOR_NO_ASIGNADO] = 1  # no deberia llegar a evaluarse

    with pytest.raises(ValidacionError, match=sql.MSG_RUT_DUPLICADO):
        validar_cartera_temporal(db)
