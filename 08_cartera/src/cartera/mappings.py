"""Nombres de tablas/hojas y especificacion de columnas de los dos Data Flows
del paquete original.

Fuente: Data Flow 'CL_TEMPORALES TBL_CARTERA' (Origen de Excel -> Conversion
de datos -> Columna derivada -> Destino OLE DB) y Data Flow 'ALIMENTA TABLA'
(Origen OLE DB -> Destino OLE DB), ambos dentro de CL_Proc_Carga_Cartera.dtsx.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Bases de datos / tablas (Connection Managers del .dtsx original)
# ---------------------------------------------------------------------------
TABLA_STAGING = "TBL_CARTERA"  # CL_TEMPORALES.dbo.TBL_CARTERA
TABLA_ACTUAL = "TBL_CARTERA_ACTUAL"  # CL_CARTERA.dbo.TBL_CARTERA_ACTUAL
# TBL_HISTORIAL_CARTERA (CL_CARTERA.dbo) no tiene constante propia: solo se
# referencia dentro de las sentencias T-SQL literales de sql.py, nunca desde
# codigo Python (a diferencia de TABLA_STAGING/TABLA_ACTUAL, que sirven de
# parametro a load.py).

# ---------------------------------------------------------------------------
# Data Flow 1: Origen de Excel 'CARTERA' (Connection Manager EXCEL)
# ---------------------------------------------------------------------------
EXCEL_SHEET = "Hoja1"

# Orden y nombres tal como los expone el Origen de Excel (26 columnas). Los
# valores de esta hoja son manuales/planos: se leen todos como texto, igual
# que el origen Excel del .dtsx (todas WSTR(255)).
EXCEL_COLUMNS: tuple[str, ...] = (
    "RUTCLI",
    "RUT_DV",
    "RUT10",
    "NOMCLI",
    "SUB_SEGME",
    "ID_GENESM",
    "RUT_SM",
    "RUT_SMDV",
    "NOM_SM",
    "MAIL_SM",
    "TELE_SM",
    "ID_GENDUP",
    "RUT_SMDUP",
    "RUT_SMDUDV",
    "NOM_SMDUP",
    "ID_GENTRI",
    "RUT_SMTRIO",
    "NOM_SMTRI",
    "RUT_SMTRDV",
    "RUT_SUP",
    "RUT_SUPDV",
    "NOM_SUP",
    "TELE_SUP",
    "MAIL_SUP",
    "SEGME",
    "ing_sspp",
)

# Columnas leidas del Excel pero descartadas por el componente 'Conversion de
# datos' (nunca se les crea una columna de salida "Copy of ..."): no llegan a
# la tabla de staging.
EXCEL_COLUMNS_DESCARTADAS: tuple[str, ...] = ("RUTCLI", "RUT10")

# Columna cuyo truncamiento en el componente 'Conversion de datos' tiene
# errorRowDisposition="IgnoreFailure" en el .dtsx original: si excede el
# ancho, se trunca en silencio. Todas las demas columnas de
# TRUNCATION_LENGTHS tienen errorRowDisposition="FailComponent": si el valor
# excede el ancho, SSIS aborta el Data Flow en vez de truncar.
TRUNCATION_TOLERANT_COLUMN = "NOMCLI"

# Anchos de truncamiento del componente 'Conversion de datos' (WSTR(255) ->
# STR(n)). OJO: 'SEGME' se trunca a 30 en el paquete original aunque la
# columna destino real admite 255 -- se replica tal cual (ver README, notas
# de fidelidad).
TRUNCATION_LENGTHS: dict[str, int] = {
    "RUT_DV": 15,
    "NOMCLI": 100,
    "SEGME": 30,
    "SUB_SEGME": 30,
    "ID_GENESM": 15,
    "RUT_SM": 15,
    "RUT_SMDV": 15,
    "NOM_SM": 50,
    "MAIL_SM": 30,
    "TELE_SM": 15,
    "ID_GENDUP": 15,
    "RUT_SMDUP": 15,
    "RUT_SMDUDV": 15,
    "NOM_SMDUP": 50,
    "ID_GENTRI": 15,
    "RUT_SMTRIO": 15,
    "NOM_SMTRI": 50,
    "RUT_SMTRDV": 15,
    "RUT_SUP": 15,
    "RUT_SUPDV": 15,
    "NOM_SUP": 50,
    "TELE_SUP": 15,
    "MAIL_SUP": 30,
    "ing_sspp": 5,
}

# Columnas y orden final insertados en TBL_CARTERA (staging), tal como las
# mapea el Destino OLE DB 'TBL_CARTERA TEMP' (26 columnas: 24 del Excel
# truncadas + 'fecha_inicio'/'fecha_fin' agregadas por la Columna derivada).
STAGING_INSERT_COLUMNS: tuple[str, ...] = (
    "RUT_DV",
    "NOMCLI",
    "SEGME",
    "SUB_SEGME",
    "ID_GENESM",
    "RUT_SM",
    "RUT_SMDV",
    "NOM_SM",
    "MAIL_SM",
    "TELE_SM",
    "ID_GENDUP",
    "RUT_SMDUP",
    "RUT_SMDUDV",
    "NOM_SMDUP",
    "ID_GENTRI",
    "RUT_SMTRIO",
    "NOM_SMTRI",
    "RUT_SMTRDV",
    "RUT_SUP",
    "RUT_SUPDV",
    "NOM_SUP",
    "TELE_SUP",
    "MAIL_SUP",
    "fecha_inicio",
    "fecha_fin",
    "ing_sspp",
)

# ---------------------------------------------------------------------------
# Data Flow 2: 'ALIMENTA TABLA' (TBL_CARTERA de CL_TEMPORALES -> TBL_CARTERA_ACTUAL
# de CL_CARTERA). Solo 21 de las 32 columnas de staging se copian, y con
# nombres distintos en destino.
# ---------------------------------------------------------------------------
ACTUAL_COLUMN_RENAME: dict[str, str] = {
    "RUT_DV": "RUT",
    "NOMCLI": "NOMBRE_CLIENTE",
    "SEGME": "SEGMENTO",
    "SUB_SEGME": "SUB_SEGMENTO",
    "ID_GENESM": "ID_GENESYS_SM_TITULAR",
    "RUT_SM": "RUT_SM_TITULAR",
    "NOM_SM": "NOM_SM_TITULAR",
    "ID_GENDUP": "ID_GENESYS_SM_DUPLA",
    "RUT_SMDUP": "RUT_SM_DUPLA",
    "NOM_SMDUP": "NOM_SM_DUPLA",
    "ID_GENTRI": "ID_GENESYS_SM_TRIADA",
    "RUT_SMTRIO": "RUT_SM_TRIADA",
    "NOM_SMTRI": "NOM_SM_TRIADA",
    "RUT_SUP": "RUT_SUPERVISOR",
    "NOM_SUP": "NOM_SUPERVISOR",
    "MAIL_SM": "MAIL_SM_TITULAR",
    "MAIL_SUP": "MAIL_SUP",
    "DNI": "COD_DNI",
    "Etiqueta": "Etiqueta",
    "RUT_SIN_DV": "RUT_SIN_DV",
    "ing_sspp": "ing_sspp",
}

# Columnas de staging leidas para 'ALIMENTA TABLA', en el orden de origen
# (antes de renombrar). Derivado de las claves de ACTUAL_COLUMN_RENAME.
ACTUAL_SOURCE_COLUMNS: tuple[str, ...] = tuple(ACTUAL_COLUMN_RENAME.keys())
