"""Tests de silver/cargar.py: reglas de ASUNTO_AGRUPADO (orden, mayusculas/tildes,
vacios) y la carga de TBL_CORREO_REGISTRO_SILVER desde bronze (por periodo
y completa)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from bronze.mappings import TABLA_BANDEJAS, TABLA_REGISTRO
from silver.cargar import (
    agrupar_asunto,
    cargar_bandejas_silver,
    cargar_periodo_silver,
    coordinador_desde_origen,
    recargar_silver_completo,
)
from silver.mappings import COLUMNAS_EXCLUIDAS_SILVER, TABLA_BANDEJAS_SILVER, TABLA_REGISTRO_SILVER
from tests.unit.fakes import FakeDatabaseGateway


@pytest.mark.parametrize(
    ("asunto", "esperado"),
    [
        ("Actualización de correo de contacto de su Service Manager", "PRESENTACIÓN"),
        ("actualizacion de correo de contacto", "PRESENTACIÓN"),
        ("PRESENTACIÓN DE SU EJECUTIVO", "PRESENTACIÓN"),
        ("Presentacion comercial", "PRESENTACIÓN"),
        ("Re: Presentación de Nueva Service Manager", "PRESENTACIÓN"),
        ("[Presentación]", "PRESENTACIÓN"),
        # palabra completa: 'presentacion' dentro de otra palabra no cuenta
        ("RE: Tecno-Aguas SpA// Documentación para representación legal", None),
        ("Presentaciones comerciales", None),
        ("Correo de PRUEBA", "PRUEBA"),
        ("[PROMOSEPTIEMBRE] ¡Beneficios exclusivos para tu empresa!", "PROMO"),
        ("[PROMOSETIEMBRE] ¡Beneficios exclusivos para tu empresa!", "PROMO"),
        ("PROMO SETIEMBRE ¡Beneficios!", "PROMO"),
        ("LLEGARON LAS PROMOCIONES PARA TU EMPRESA", "PROMO"),
        ("Delivery Status Notification (Failure)", "REBOTE"),
        ("Fwd: Delivery Status Notification (Failure)", "REBOTE"),
        ("Notificacion de estado de entrega", "REBOTE"),
        ("Undelivered Mail Returned to Sender.", "REBOTE"),
        ("Re: COTIZACION LINEA+EQUIPO", None),
        ("", None),
        ("   ", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_agrupar_asunto(asunto, esperado):
    assert agrupar_asunto(asunto) == esperado


def test_rebote_tiene_prioridad_sobre_presentacion():
    # Un rebote cita el asunto original: debe contar como rebote.
    assert agrupar_asunto("No entregable: Actualización de correo de contacto de su Service Manager") == "REBOTE"


def _bronze_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FechaHora_UTC_Texto": [datetime(2026, 9, 5), datetime(2026, 9, 6)],
            "Asunto": ["Correo de prueba", "Re: consulta"],
            "ID_Mensaje": ["MSG-1", "MSG-2"],
            "ORIGEN": ["Registro_JHON_MORALES_PENA.xlsx", None],
        }
    )


def test_cargar_periodo_silver_lee_bronze_y_reemplaza_el_periodo():
    gateway = FakeDatabaseGateway()
    gateway.resultado_select = _bronze_df()
    gateway.filas_a_eliminar = 5
    fecha_inicio, fecha_fin = datetime(2026, 9, 1), datetime(2026, 10, 1)

    eliminadas, insertadas = cargar_periodo_silver(gateway, fecha_inicio, fecha_fin)

    sql_select, params_select = gateway.selects[0]
    assert TABLA_REGISTRO in sql_select and "WHERE" in sql_select
    assert params_select == (fecha_inicio, fecha_fin)
    # Los calculos del Excel no confiables quedan solo en bronze.
    for columna in COLUMNAS_EXCLUIDAS_SILVER:
        assert f"[{columna}]" not in sql_select

    sql_delete, params_delete = gateway.deletes[0]
    assert TABLA_REGISTRO_SILVER in sql_delete
    assert params_delete == (fecha_inicio, fecha_fin)

    insertado = gateway.inserted[TABLA_REGISTRO_SILVER]
    assert list(insertado["ASUNTO_AGRUPADO"]) == ["PRUEBA", None]
    assert list(insertado["COORDINADOR"]) == ["JHON MORALES PENA", None]
    assert (eliminadas, insertadas) == (5, 2)


def test_recargar_silver_completo_trunca_y_lee_todo_bronze():
    gateway = FakeDatabaseGateway()
    gateway.resultado_select = _bronze_df()

    insertadas = recargar_silver_completo(gateway)

    sql_select, params_select = gateway.selects[0]
    assert "WHERE" not in sql_select
    assert params_select == ()
    assert gateway.truncated_tables == [TABLA_REGISTRO_SILVER]
    assert gateway.deletes == []
    assert insertadas == 2


@pytest.mark.parametrize(
    ("origen", "esperado"),
    [
        ("Registro_JHON_MORALES_PENA.xlsx", "JHON MORALES PENA"),
        ("registro_ana_perez.XLSX", "ana perez"),  # prefijo sin distinguir mayusculas
        ("Registro_RODRIGUEZ_ALEY_DE_GARCIA_MARITZA_JOHANNA.xlsm", "RODRIGUEZ ALEY DE GARCIA MARITZA JOHANNA"),
        ("OTRO_ARCHIVO.xlsx", "OTRO ARCHIVO"),  # sin prefijo: se conserva el nombre
        ("Registro_.xlsx", None),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_coordinador_desde_origen(origen, esperado):
    assert coordinador_desde_origen(origen) == esperado


def test_cargar_bandejas_silver_reemplaza_completo_y_agrega_coordinador():
    gateway = FakeDatabaseGateway()
    gateway.resultado_select = pd.DataFrame(
        {
            "Correo_Bandeja": ["SM1@movistar.cl", "SM2@movistar.cl"],
            "Asesor": ["A", "B"],
            "UltimaRevisionEntrada": [datetime(2026, 9, 22), None],
            "UltimaRevisionSalida": [None, None],
            "ORIGEN": ["Registro_JHON_MORALES_PENA.xlsx", "Registro_ALICIA_DEL_VALLE_SANCHEZ_NAMIAS.xlsx"],
        }
    )

    insertadas = cargar_bandejas_silver(gateway)

    sql_select, params_select = gateway.selects[0]
    assert f"[{TABLA_BANDEJAS}]" in sql_select and "WHERE" not in sql_select
    assert gateway.truncated_tables == [TABLA_BANDEJAS_SILVER]
    assert list(gateway.inserted[TABLA_BANDEJAS_SILVER]["COORDINADOR"]) == [
        "JHON MORALES PENA",
        "ALICIA DEL VALLE SANCHEZ NAMIAS",
    ]
    assert insertadas == 2
