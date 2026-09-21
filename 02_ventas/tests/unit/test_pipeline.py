from datetime import date

import pandas as pd

import mappings
from pipeline import VentasPipeline
from tests.unit.fakes import FakeDatabaseGateway, FakeSharePointCsvReader, FakeSharePointExcelReader


def _fila_senhalizaciones(**overrides) -> dict:
    fila = {origen: "x" for origen, _destino in mappings.MAPEO_SENHALIZACIONES}
    fila.update(overrides)
    return fila


def _fila_dni(**overrides) -> dict:
    fila = {"DNI ORIGEN": "1", "DNI A CAMBIAR": "2", "Observación": "obs"}
    fila.update(overrides)
    return fila


def _fila_ventas_basev2(**overrides) -> dict:
    fila = {}
    for c in mappings.COLUMNAS_VENTAS_BASEV2:
        if c.tipo in ("numero", "entero"):
            fila[c.nombre] = "1"
        elif c.tipo == "fecha":
            fila[c.nombre] = "2026-08-15"
        else:
            fila[c.nombre] = "x"
    fila.update(overrides)
    return fila


def _fila_rango_comisiones(**overrides) -> dict:
    fila = {c: (1.0 if c != "CARGO" else "x") for c in mappings.COLUMNAS_VENTAS_RANGO_COMISIONES}
    fila.update(overrides)
    return fila


def _fila_metas(**overrides) -> dict:
    fila = {
        "Plataforma": "p", "Cargo": "c", "Nombre": "n", "BG_DNI": "1", "DNI": "1",
        "PUSHER A CARGO": "x", "Fibra": 1.0, "Voz": 1.0, "Total": 1.0, "PERIODO": 202608.0,
        "Señalizacion Total": "1",
    }
    fila.update(overrides)
    return fila


def _build_pipeline(
    senhalizaciones_rows=None,
    dni_rows=None,
    basev2_rows=None,
    esp_rows=None,
    sup_rows=None,
    rango_comisiones_rows=None,
    metas_rows=None,
    basev2_temp_tabla=None,
    rowcount_results=None,
):
    db = FakeDatabaseGateway()
    if rowcount_results is not None:
        db.rowcount_results = list(rowcount_results)
    if basev2_temp_tabla is not None:
        db.tables[mappings.TABLA_VENTAS_BASEV2_TEMP] = basev2_temp_tabla

    csv_reader = FakeSharePointCsvReader(
        {mappings.ARCHIVO_SENHALIZACIONES_CSV: pd.DataFrame(senhalizaciones_rows or [_fila_senhalizaciones()])}
    )
    excel_reader = FakeSharePointExcelReader(
        {
            (mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_DNI_SENALIZACIONES): pd.DataFrame(dni_rows or [_fila_dni()]),
            (mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_BASEV2): pd.DataFrame(basev2_rows or [_fila_ventas_basev2()]),
            (mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_ESP): pd.DataFrame(esp_rows or [{"DNI": "1", "Especialista": "x"}]),
            (mappings.ARCHIVO_FUNNEL_VENTAS_XLSX, mappings.HOJA_SUP): pd.DataFrame(sup_rows or [{"DNI": "1", "SUPERVISOR": "x"}]),
            (mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_COMISIONES_MES): pd.DataFrame(
                rango_comisiones_rows or [_fila_rango_comisiones()]
            ),
            (mappings.ARCHIVO_BASE_CARTA_META_XLSX, mappings.HOJA_METAS): pd.DataFrame(metas_rows or [_fila_metas()]),
        }
    )
    pipeline = VentasPipeline(db=db, csv_reader=csv_reader, excel_reader=excel_reader)
    return pipeline, db


def test_ejecutar_senalizaciones_trunca_antes_de_cargar_y_corre_en_orden():
    pipeline, db = _build_pipeline()

    resultado = pipeline.ejecutar_senalizaciones()

    # Los TRUNCATE se ejecutan como script T-SQL literal (3 partes,
    # [CL_USUARIOS].[dbo].[tabla]), no via DatabaseGateway.truncate_table().
    scripts_sql = [s for s, _ in db.executed_scripts]
    assert any(mappings.TABLA_SENHALIZACIONES in s and "TRUNCATE" in s for s in scripts_sql)
    assert any(mappings.TABLA_SENHALIZACIONES_DNI in s and "TRUNCATE" in s for s in scripts_sql)
    assert mappings.TABLA_SENHALIZACIONES in db.inserted
    assert mappings.TABLA_SENHALIZACIONES_DNI in db.inserted
    assert resultado.nombre == "senalizaciones"
    assert resultado.filas_por_paso["TBL_FUNNEL_SENHALIZACIONES"] == 1
    assert resultado.filas_por_paso["TBL_FUNNEL_SENHALIZACIONES_DNI"] == 1

    # El SP y las correcciones de DNI corren despues de cargar la tabla principal.
    scripts_sql = [s for s, _ in db.executed_scripts]
    assert any("SP_FUNNEL_SENHALIZACIONES" in s for s in scripts_sql)


def test_ejecutar_senalizaciones_deja_vacio_un_valor_muy_largo_sin_abortar():
    # A pedido del usuario: un valor que excede el ancho de la columna se
    # deja vacio y la fila se carga igual, en vez de abortar toda la carga
    # (comportamiento FailComponent del .dtsx original, ya no vigente aqui).
    fila = _fila_senhalizaciones(Coordinador="x" * 51)  # maximo 50
    pipeline, db = _build_pipeline(senhalizaciones_rows=[fila])

    resultado = pipeline.ejecutar_senalizaciones()

    assert resultado.filas_por_paso["TBL_FUNNEL_SENHALIZACIONES"] == 1
    cargado = db.inserted[mappings.TABLA_SENHALIZACIONES]
    assert pd.isna(cargado["COORDINADOR"].iloc[0])


def test_ejecutar_ventas_carga_las_6_tablas_y_corre_local_al_final():
    basev2_temp = pd.DataFrame([_fila_ventas_basev2()])
    for extra in mappings.COLUMNAS_VENTAS_BASEV2_POST_CARGA:
        basev2_temp[extra] = "x"
    pipeline, db = _build_pipeline(basev2_temp_tabla=basev2_temp, rowcount_results=[3, 2, 1])

    resultado = pipeline.ejecutar_ventas(date(2026, 8, 1))

    assert resultado.nombre == "ventas"
    for tabla in (
        mappings.TABLA_VENTAS_RANGO_COMISIONES,
        mappings.TABLA_SENHALIZACIONES_DNI,
        mappings.TABLA_METAS_COMISIONES,
        mappings.TABLA_VENTAS_BASEV2_TEMP,
        mappings.TABLA_VENTAS_ESP_TEMP,
        mappings.TABLA_VENTAS_SUP_TEMP,
        mappings.TABLA_VENTAS_TEMP,
    ):
        assert tabla in db.inserted, f"no se cargo {tabla}"

    # LOCAL corre al final: DELETE VENTAS2 >=, DELETE TEMP <, INSERT VENTAS2 (rowcount, en ese orden).
    assert len(db.executed_rowcount_scripts) == 3
    assert "TBL_FUNNEL_VENTAS2" in db.executed_rowcount_scripts[0][0]
    assert "TBL_FUNNEL_VENTAS_Temp" in db.executed_rowcount_scripts[1][0]
    assert "INSERT" in db.executed_rowcount_scripts[2][0]
    assert resultado.filas_por_paso["DELETE VENTAS2 >="] == 3
    assert resultado.filas_por_paso["DELETE TEMP <"] == 2
    assert resultado.filas_por_paso["INSERT VENTAS2"] == 1


def test_local_recastea_numericos_tras_roundtrip_sql_evita_punto_cero():
    # Reproduce el bug real (2026-09-17): TBL_FUNNEL_VENTAS_basev2_temp.[TOTAL
    # INGRESADO] es 'int' en SQL Server, pero al releerla con
    # db.read_table()/pd.DataFrame.from_records() (extractor.extraer_ventas_basev2_temp),
    # una columna con algun NULL sube a float64 -- un valor 1 se vuelve 1.0, y
    # como TBL_FUNNEL_VENTAS_Temp/TBL_FUNNEL_VENTAS2 son 'nvarchar' (no
    # numericas), ese 1.0 se insertaba literalmente como texto '1.0' en vez de
    # '1'. Se simula aqui la misma columna float64 con nulos que devolveria
    # el roundtrip real.
    basev2_temp = pd.DataFrame([_fila_ventas_basev2(), _fila_ventas_basev2()])
    for extra in mappings.COLUMNAS_VENTAS_BASEV2_POST_CARGA:
        basev2_temp[extra] = "x"
    basev2_temp["TOTAL INGRESADO"] = pd.array([1.0, None], dtype="float64")

    pipeline, db = _build_pipeline(basev2_temp_tabla=basev2_temp)
    pipeline.ejecutar_ventas(date(2026, 8, 1))

    cargado = db.inserted[mappings.TABLA_VENTAS_TEMP]
    assert cargado["TOTAL INGRESADO"].iloc[0] == 1
    assert str(cargado["TOTAL INGRESADO"].iloc[0]) != "1.0"
    assert pd.isna(cargado["TOTAL INGRESADO"].iloc[1])


def test_ejecutar_ventas_completa_dni_sup_esp_despues_de_cargar_basev2_esp_sup():
    basev2_temp = pd.DataFrame([_fila_ventas_basev2()])
    for extra in mappings.COLUMNAS_VENTAS_BASEV2_POST_CARGA:
        basev2_temp[extra] = "x"
    pipeline, db = _build_pipeline(basev2_temp_tabla=basev2_temp)

    pipeline.ejecutar_ventas(date(2026, 8, 1))

    scripts_sql = [s for s, _ in db.executed_scripts]
    idx_carga_basev2 = list(db.inserted.keys()).index(mappings.TABLA_VENTAS_BASEV2_TEMP)
    assert idx_carga_basev2 >= 0
    assert any("DNI SUPERVISOR" in s for s in scripts_sql)


def test_ejecutar_todo_corre_senalizaciones_antes_de_ventas():
    basev2_temp = pd.DataFrame([_fila_ventas_basev2()])
    for extra in mappings.COLUMNAS_VENTAS_BASEV2_POST_CARGA:
        basev2_temp[extra] = "x"
    pipeline, db = _build_pipeline(basev2_temp_tabla=basev2_temp, rowcount_results=[1, 1, 1])

    resultado = pipeline.ejecutar_todo(date(2026, 8, 1))

    assert [r.nombre for r in resultado.resultados] == ["senalizaciones", "ventas"]
    # La tabla de Señalizaciones se trunco/cargo antes que cualquier tabla de Ventas
    # (orden de inserciones refleja el orden real de ejecucion, dict preserva orden).
    orden_tablas = list(db.inserted.keys())
    assert orden_tablas.index(mappings.TABLA_SENHALIZACIONES) < orden_tablas.index(mappings.TABLA_VENTAS_RANGO_COMISIONES)
