"""Sentencias T-SQL migradas literalmente desde los Execute SQL Task de
SSIS_Chile_parque.dtsx.

Fase 1: las tareas 'TRUNCATE' de 'PQ FIJO I' / 'PQ MOVIL I' se documentan
aqui como referencia/equivalencia --igual que en 08_cartera/sql.py-- aunque
en codigo se generan de forma generica desde
db.DatabaseGateway.truncate_table(tabla).

Fase 2: las tareas 'DELETE ... WHERE PERIODO = ?' de 'PQ FIJO II' / 'PQ
MOVIL II' SI se ejecutan tal cual desde estas constantes (ver
mappings.FIJO_SPEC.sql_delete_historico / MOVIL_SPEC.sql_delete_historico y
carga/loader.borrar_historico_periodo). El Data Flow que le sigue a cada
DELETE en el .dtsx original volvia a leer Externos_Frac con la misma
consulta que 'PQ FIJO I'/'PQ MOVIL I'; en esta migracion se disenio para
leer en cambio desde la tabla _ACTUAL ya cargada por la Fase 1 (ver README,
seccion 'Fase 2'), por lo que ese INSERT se arma de forma generica en
carga/loader.insertar_historico_desde_actual (columnas de
ParqueFlowSpec.nombres_columnas), no como constante literal aqui.
"""

from __future__ import annotations

TRUNCATE_FIJO_ACTUAL = "TRUNCATE TABLE [CL_PLANTA].[dbo].[TBL_PARQUE_FIJO_ACTUAL]"
TRUNCATE_MOVIL_ACTUAL = "TRUNCATE TABLE [CL_PLANTA].[dbo].[TBL_PARQUE_MOVIL_ACTUAL]"

DELETE_FIJO_HISTORICO = "DELETE [CL_PLANTA].[dbo].[TBL_PARQUE_FIJO_HISTORICO] WHERE PERIODO = ?"
DELETE_MOVIL_HISTORICO = "DELETE [CL_PLANTA].[dbo].[TBL_PARQUE_MOVIL_HISTORICO] WHERE PERIODO = ?"
