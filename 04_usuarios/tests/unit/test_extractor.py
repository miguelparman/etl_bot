import pandas as pd
import pytest

import sql
from exceptions import ExtraccionError
from extraccion import extractor
from models import Periodo
from tests.unit.fakes import FakeDatabaseGateway


def test_extraer_parque_consulta_externos_frac_con_periodo_en_los_3_parametros():
    db_externos_frac = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"periodo": 202608, "segme": "MICRO", "pqe": 1}])
    db_externos_frac.query_results[sql.PARQUE_SELECT] = esperado
    periodo = Periodo("202608")

    resultado = extractor.extraer_parque(db_externos_frac, periodo)

    pd.testing.assert_frame_equal(resultado, esperado)
    consulta, params = db_externos_frac.queries_ejecutadas[0]
    assert consulta == sql.PARQUE_SELECT
    assert params == ("202608", "202608", "202608")


def test_extraer_bajas_fraude_consulta_con_periodo():
    db_externos_frac = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"PERIODO": 202608}])
    db_externos_frac.query_results[sql.RETENCIONES_BAJAS_FRAUDE_SELECT] = esperado

    resultado = extractor.extraer_bajas_fraude(db_externos_frac, Periodo("202608"))

    pd.testing.assert_frame_equal(resultado, esperado)
    assert db_externos_frac.queries_ejecutadas[0] == (sql.RETENCIONES_BAJAS_FRAUDE_SELECT, ("202608",))


def test_extraer_bajas_por_alta_consulta_con_periodo():
    db_externos_frac = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"PERIODO": 202608}])
    db_externos_frac.query_results[sql.RETENCIONES_BAJAS_POR_ALTA_SELECT] = esperado

    resultado = extractor.extraer_bajas_por_alta(db_externos_frac, Periodo("202608"))

    pd.testing.assert_frame_equal(resultado, esperado)
    assert db_externos_frac.queries_ejecutadas[0] == (sql.RETENCIONES_BAJAS_POR_ALTA_SELECT, ("202608",))


def _fila_bd_reten(**overrides) -> dict:
    fila = {
        "ROWNO": 1,
        "periodo": 202608,
        "rut": "123456785",
        "rutcli": 12345678,
        "nomcli": "CLIENTE X",
        "segme": "MEDIANA",
        "nom_sm": "ASESOR X",
        "nom_sup": "SUPERVISOR X",
        "sub_segme": "SUB X",
        "tpo_serv": "FIJO",
        "tpo_prod": "BAF",
        "tpo_tecno": "FO",
        "q_parque": 1,
        "q_riesgo": 0,
        "q_baja_v": 0,
        "q_baja_p": 0,
        "q_baja_m": 0,
        "motivo": "MOTIVO SIN USO",
        "submotivo": "BAJA SIN RETENCION",
        "submotivo2": "",
        "canal_ing": "CALL",
        "subcan_ing": "IN",
        "canal_res": "CALL",
        "subcan_res": "OUT",
        "cargo_res": "AGENTE",
        "canal_hres": "CALL",
        "last_modified": "2026-08-01 10:00:00",
        "case_idnum": "12345",
        "Evaluacion": 1,
        "LLAVE": "202608123456785FIJOBAFFO",
    }
    fila.update(overrides)
    return fila


def test_extraer_bd_reten_descarta_rowno_y_motivo_y_convierte_evaluacion_y_fecha():
    db_externos_frac = FakeDatabaseGateway()
    db_externos_frac.query_results[sql.RETENCIONES_BD_RETEN_SELECT] = pd.DataFrame([_fila_bd_reten()])

    resultado = extractor.extraer_bd_reten(db_externos_frac, Periodo("202608"))

    assert "ROWNO" not in resultado.columns
    assert "motivo" not in resultado.columns
    assert resultado.loc[0, "Evaluacion"] == "1"
    assert str(resultado.loc[0, "last_modified"]) == "2026-08-01"
    assert db_externos_frac.queries_ejecutadas[0] == (sql.RETENCIONES_BD_RETEN_SELECT, ("202608",))


def test_extraer_bd_reten_aborta_si_una_columna_excede_el_ancho_de_truncamiento():
    db_externos_frac = FakeDatabaseGateway()
    fila = _fila_bd_reten(nomcli="X" * 101)  # mappings.BD_RETEN_TRUNCATION_LENGTHS["nomcli"] == 100
    db_externos_frac.query_results[sql.RETENCIONES_BD_RETEN_SELECT] = pd.DataFrame([fila])

    with pytest.raises(ExtraccionError):
        extractor.extraer_bd_reten(db_externos_frac, Periodo("202608"))


def test_extraer_bajas_fijo_consulta_con_periodo():
    db_externos_frac = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"YEAR_MONTH": 202608}])
    db_externos_frac.query_results[sql.INTENCIONES_BAJAS_FIJO_SELECT] = esperado

    resultado = extractor.extraer_bajas_fijo(db_externos_frac, Periodo("202608"))

    pd.testing.assert_frame_equal(resultado, esperado)
    assert db_externos_frac.queries_ejecutadas[0] == (sql.INTENCIONES_BAJAS_FIJO_SELECT, ("202608",))


def test_extraer_bajas_movil_consulta_con_periodo():
    db_externos_frac = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"PERIODO": 202608}])
    db_externos_frac.query_results[sql.INTENCIONES_BAJAS_MOVIL_SELECT] = esperado

    resultado = extractor.extraer_bajas_movil(db_externos_frac, Periodo("202608"))

    pd.testing.assert_frame_equal(resultado, esperado)
    assert db_externos_frac.queries_ejecutadas[0] == (sql.INTENCIONES_BAJAS_MOVIL_SELECT, ("202608",))


def test_extraer_usuarios_retenciones_consulta_sin_parametros():
    db_cl_usuarios = FakeDatabaseGateway()
    esperado = pd.DataFrame([{"Believe": "x", "Programa": "retencion chile", "Periodo": 202608}])
    db_cl_usuarios.query_results[sql.INTENCIONES_USUARIOS_RETENCIONES_SELECT] = esperado

    resultado = extractor.extraer_usuarios_retenciones(db_cl_usuarios)

    pd.testing.assert_frame_equal(resultado, esperado)
    assert db_cl_usuarios.queries_ejecutadas[0] == (sql.INTENCIONES_USUARIOS_RETENCIONES_SELECT, ())


def test_extraer_intenciones_v2_aborta_si_case_id_number_excede_15():
    db_externos_frac = FakeDatabaseGateway()
    fila = {"CASE_ID_NUMBER": "1" * 20, "CASE_OPEN_TIME": "2026-08-01", "CASE_NOTE": "nota"}
    db_externos_frac.query_results[sql.INTENCIONES_V2_SELECT] = pd.DataFrame([fila])

    with pytest.raises(ExtraccionError):
        extractor.extraer_intenciones_v2(db_externos_frac, Periodo("202608"))


def test_extraer_intenciones_v2_no_aborta_si_case_id_number_no_excede_15():
    db_externos_frac = FakeDatabaseGateway()
    fila = {"CASE_ID_NUMBER": "12345", "CASE_OPEN_TIME": "2026-08-01", "CASE_NOTE": "nota"}
    db_externos_frac.query_results[sql.INTENCIONES_V2_SELECT] = pd.DataFrame([fila])

    resultado = extractor.extraer_intenciones_v2(db_externos_frac, Periodo("202608"))

    assert resultado.loc[0, "CASE_ID_NUMBER"] == "12345"


def _fila_item_amdocs(**overrides) -> dict:
    fila = {
        "ROWNO": 1,
        "rut": 12345678,
        "case_idnum": 36110065,
        "type1": "TIPO1",
        "type2": "TIPO2",
        "sub_motivo": "SUBMOTIVO",
        "case_desc": "DESCRIPCION",
        "case_resol": "RESOLUCION",
        "case_optim": "2026-08-01 10:00:00",
        "agent_orig": 111,
        "agent_reso": 222,
        "canal_ing": "CALL",
        "subcan_ing": "IN",
        "case_cltim": "2026-08-01 12:00:00",
        "segmento": "MASIVO",
        "subtype": "SUBTIPO",
        "line_buss": "FIJA",
        "motivo": "MOTIVO",
        "servicio": "BAF",
        "cantidad": 1,
        "prod_type": "BAF",
        "ser_stat_r": "OK",
        "periodo": 202608,
        "tpo_serv": "FIJO",
        "rutcli": 12345678,
        "pqe_stb": 0,
        "pqe_baf": 1,
        "pqe_tv": 0,
        "pqe_voz": 0,
        "pqe_bam": 0,
        "tecno_stb": "",
        "tecno_baf": "FO",
        "tecno_tv": "",
        "tpo_t_stb": "",
        "tpo_t_baf": "CO",
        "tpo_t_tv": "",
        "origen": "WEB",
        "canal_res": "CALL",
        "subcan_res": "OUT",
        "cargo_res": "AGENTE",
        "canal_hres": "CALL",
        "ValidFrom": "2026-08-15 00:00:00",
    }
    fila.update(overrides)
    return fila


def test_extraer_item_amdocs_descarta_rutcli_y_renombra_rowno_a_evaluacion():
    db_externos_frac = FakeDatabaseGateway()
    db_externos_frac.query_results[sql.ITEM_AMDOCS_SELECT] = pd.DataFrame([_fila_item_amdocs()])

    resultado = extractor.extraer_item_amdocs(db_externos_frac, Periodo("202608"))

    assert "rutcli" not in resultado.columns
    assert "ROWNO" not in resultado.columns
    assert resultado.loc[0, "Evaluacion"] == 1
    assert db_externos_frac.queries_ejecutadas[0] == (sql.ITEM_AMDOCS_SELECT, ("202608",))


def test_extraer_item_amdocs_no_aborta_si_un_entero_no_castea_ignorefailure():
    db_externos_frac = FakeDatabaseGateway()
    fila = _fila_item_amdocs(agent_reso="no-numerico")
    db_externos_frac.query_results[sql.ITEM_AMDOCS_SELECT] = pd.DataFrame([fila])

    resultado = extractor.extraer_item_amdocs(db_externos_frac, Periodo("202608"))

    assert pd.isna(resultado.loc[0, "agent_reso"])


def test_extraer_item_amdocs_trunca_en_silencio_sin_abortar_ignorefailure():
    db_externos_frac = FakeDatabaseGateway()
    fila = _fila_item_amdocs(case_desc="X" * 500)  # mappings.ITEM_AMDOCS_TRUNCATION_LENGTHS["case_desc"] == 450
    db_externos_frac.query_results[sql.ITEM_AMDOCS_SELECT] = pd.DataFrame([fila])

    resultado = extractor.extraer_item_amdocs(db_externos_frac, Periodo("202608"))

    assert len(resultado.loc[0, "case_desc"]) == 450


def test_extraer_saip_descarta_fec_saip_a_y_b_y_convierte_fechas():
    db_externos_frac = FakeDatabaseGateway()
    fila = {
        "rut_ej": "1",
        "dv_ej": "2",
        "fec_ingr": "2020-01-15",
        "FECHA": "15/01/2022",
        "fec_saip_a": "2022-01-15",
        "fec_saip_b": "2022-01-16",
        "autentica": "SI",
    }
    db_externos_frac.query_results[sql.SAIP_SELECT] = pd.DataFrame([fila])

    resultado = extractor.extraer_saip(db_externos_frac)

    assert "fec_saip_a" not in resultado.columns
    assert "fec_saip_b" not in resultado.columns
    assert str(resultado.loc[0, "fec_ingr"]) == "2020-01-15"
    assert str(resultado.loc[0, "FECHA"]) == "2022-01-15"
    assert db_externos_frac.queries_ejecutadas[0] == (sql.SAIP_SELECT, ())
