"""Especificacion de columnas/tablas/anchos de las 2 ramas de
SSIS_Chile_parque.dtsx ('PQ FIJO I', 'PQ MOVIL I'), Fase 1 (solo _ACTUAL).

Fuente: Origen OLE DB 'PQE_FIJO' (SELECT ... FROM [Externos_Frac].[dbo].
[pqe_fijtot2023] WHERE periodo = ?) y 'PQE_MO' (... [pqe_movtot2023] ...),
cada uno con su Destino OLE DB (TBL_PARQUE_FIJO_ACTUAL / TBL_PARQUE_MOVIL_
ACTUAL en CL_PLANTA). Los anchos de columna son los declarados en el
Origen OLE DB del .dtsx original (DT_STR); se preservan tal cual, incluida
la diferencia de largo de 'rutcli' entre ambas tablas (50 en FIJO, 10 en
MOVIL) -- ver README, seccion 'Notas de fidelidad'.

El nombre de archivo CSV coincide, a proposito, con el nombre de la tabla de
origen SQL Server que reemplaza (pqe_fijtot2023.csv / pqe_movtot2023.csv).
"""

from __future__ import annotations

import sql
from models import ColumnaSpec, ParqueFlowSpec

# ---------------------------------------------------------------------------
# Columna usada para el filtro equivalente a 'WHERE periodo = ?' del Origen
# OLE DB original (variable de paquete User::Periodo).
# ---------------------------------------------------------------------------
COLUMNA_PERIODO = "periodo"

# Delimitador de los CSV publicados en SharePoint. Confirmado contra el
# archivo real: ';' (no ',' como se habia asumido inicialmente a partir del
# .dtsx, que no declara delimitador porque el origen original era SQL
# Server, no un archivo plano). Los nombres de columna si coincidian
# exactamente con lo esperado.
CSV_DELIMITER = ";"

# ---------------------------------------------------------------------------
# PQ FIJO I: Origen 'PQE_FIJO' -> Destino 'TBL_PARQUE_FIJO_ACTUAL'
# ---------------------------------------------------------------------------
FIJO_COLUMNS: tuple[ColumnaSpec, ...] = (
    ColumnaSpec("periodo", 100),
    ColumnaSpec("rut", 50),
    ColumnaSpec("segme", 100),
    ColumnaSpec("ciclo", 100),
    ColumnaSpec("telefono", 100),
    ColumnaSpec("subs_key", 100),
    ColumnaSpec("access_id", 100),
    ColumnaSpec("tpo_prod", 100),
    ColumnaSpec("q_casos", 100),
    ColumnaSpec("tecnologia", 100),
    ColumnaSpec("rutcli", 50),
)

FIJO_SPEC = ParqueFlowSpec(
    nombre="PQ FIJO I",
    archivo_csv="pqe_fijtot2023.csv",
    tabla_destino="TBL_PARQUE_FIJO_ACTUAL",
    columnas=FIJO_COLUMNS,
    nombre_historico="PQ FIJO II",
    tabla_historico="TBL_PARQUE_FIJO_HISTORICO",
    sql_delete_historico=sql.DELETE_FIJO_HISTORICO,
)

# ---------------------------------------------------------------------------
# PQ MOVIL I: Origen 'PQE_MO' -> Destino 'TBL_PARQUE_MOVIL_ACTUAL'
# ---------------------------------------------------------------------------
MOVIL_COLUMNS: tuple[ColumnaSpec, ...] = (
    ColumnaSpec("periodo", 100),
    ColumnaSpec("rut", 100),
    ColumnaSpec("segme", 100),
    ColumnaSpec("telefono", 100),
    ColumnaSpec("tpo_prod", 100),
    ColumnaSpec("cta_finan", 100),
    ColumnaSpec("rutcli", 10),  # OJO: 10 en MOVIL vs 50 en FIJO, se preserva la diferencia
)

MOVIL_SPEC = ParqueFlowSpec(
    nombre="PQ MOVIL I",
    archivo_csv="pqe_movtot2023.csv",
    tabla_destino="TBL_PARQUE_MOVIL_ACTUAL",
    columnas=MOVIL_COLUMNS,
    nombre_historico="PQ MOVIL II",
    tabla_historico="TBL_PARQUE_MOVIL_HISTORICO",
    sql_delete_historico=sql.DELETE_MOVIL_HISTORICO,
)
