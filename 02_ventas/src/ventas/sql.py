"""Sentencias T-SQL migradas literalmente de cada Execute SQL Task de los
.dtsx originales. Ver README, "Notas de fidelidad", para los casos donde el
texto original no es SQL valido tal cual (p.ej. el separador 'GO')."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CROSS 0101 SSIS_CL_Senalizaciones.dtsx
# ---------------------------------------------------------------------------

SQL_TRUNCATE_SENHALIZACIONES_DNI = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES_DNI]"

SQL_TRUNCATE_SENHALIZACIONES = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES]"

SQL_EXEC_SP_FUNNEL_SENHALIZACIONES = "EXEC [CL_USUARIOS].[dbo].[SP_FUNNEL_SENHALIZACIONES]"

# Execute SQL Task 'UPDATE' (interno, dentro de 'Contenedor de secuencias'):
# aplica a TBL_FUNNEL_SENHALIZACIONES.[TU DNI] la correccion cargada en
# TBL_FUNNEL_SENHALIZACIONES_DNI (columna 'DNI A CAMBIAR' donde no es NULL).
SQL_CORREGIR_DNI_DESDE_TABLA_DNI = """
WITH nuevo_dni as
(
SELECT [DNI ORIGEN]
      ,[DNI A CAMBIAR]
      ,[Observación]
  FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES_DNI]
  WHERE [DNI A CAMBIAR] IS NOT NULL
)


UPDATE x0
SET
	[TU DNI] = x1.[DNI A CAMBIAR]
FROM
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES] x0
INNER JOIN
	nuevo_dni x1
ON
	x1.[DNI ORIGEN] = x0.[TU DNI]
"""

# Execute SQL Task 'UPDATE' (outer, nivel 'Contenedor de secuencias 1'):
# 19 sentencias UPDATE separadas por 'GO' en el .dtsx original -- 'GO' no es
# una instruccion T-SQL valida para el proveedor OLEDB del Execute SQL Task,
# asi que aqui se ejecuta como 1 UPDATE parametrizado por cada par de
# mappings.CORRECCIONES_DNI_CEROS (misma logica exacta, ver transformer.py).
SQL_CORREGIR_DNI_CERO_PERDIDO = "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES] SET [TU DNI] = ? WHERE [TU DNI] = ?"

# ---------------------------------------------------------------------------
# CROSS 0102 SSIS_CL_Ventas.dtsx
# ---------------------------------------------------------------------------

SQL_TRUNCATE_VENTAS_BASEV2_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]"
SQL_TRUNCATE_VENTAS_ESP_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Esp_temp]"
SQL_TRUNCATE_VENTAS_SUP_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Sup_temp]"
SQL_TRUNCATE_VENTAS_RANGO_COMISIONES = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_VENTAS_RANGO_COMISIONES]"
SQL_TRUNCATE_METAS_COMISIONES = "TRUNCATE TABLE METAS_COMISIONES"
SQL_TRUNCATE_VENTAS_TEMP = "TRUNCATE TABLE [dbo].TBL_FUNNEL_VENTAS_Temp"

# Execute SQL Task 'BaseV2\Tarea Ejecutar SQL': 5 sentencias separadas por
# 'GO' en el .dtsx original -- se ejecutan en orden, cada una por separado
# (mismo motivo que SQL_CORREGIR_DNI_CERO_PERDIDO: 'GO' no es SQL valido
# para el proveedor OLEDB del Execute SQL Task).
SQL_LIMPIEZA_VENTAS_BASEV2: tuple[str, ...] = (
    "DELETE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]\nWHERE [Fecha Ingreso] is null",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]\nSET [RUT EJECUTIVO] = TRIM([RUT EJECUTIVO])",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]\nSET ESTADO = UPPER(TRIM(ESTADO))",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] \n"
    "SET [Rut Empresa] = LEFT(TRIM(REPLACE([Rut Empresa],'-','')),LEN([Rut Empresa]) - 2)\n"
    "WHERE LEN([Rut Empresa])>2",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]\n"
    "SET [FECHA DE EVALUACION] = \n"
    "\t\t\t\t\t\t\tCASE\n"
    "\t\t\t\t\t\t\t\tWHEN ESTADO = 'TERMINADO' AND [FECHA HABILITACION] IS NOT NULL THEN CAST([FECHA HABILITACION] AS date)\n"
    "\t\t\t\t\t\t\t\tELSE CAST([Fecha Ingreso] AS date)\n"
    "\t\t\t\t\t\t\tEND",
)

# Execute SQL Task 'BaseV2\update DNI': aplica a basev2_temp.[RUT EJECUTIVO]
# la correccion cargada en TBL_FUNNEL_SENHALIZACIONES_DNI (misma logica que
# SQL_CORREGIR_DNI_DESDE_TABLA_DNI de Señalizaciones, pero sobre otra tabla/columna).
SQL_ACTUALIZAR_RUT_EJECUTIVO_DESDE_TABLA_DNI = """
WITH nuevo_dni as
(
SELECT
    [DNI ORIGEN]
    ,[DNI A CAMBIAR]
    ,[Observación]
FROM
    [CL_USUARIOS].[dbo].[TBL_FUNNEL_SENHALIZACIONES_DNI]
WHERE
    [DNI A CAMBIAR] IS NOT NULL
)


UPDATE x0
SET
    [RUT EJECUTIVO] = x1.[DNI A CAMBIAR]
FROM
    [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0
INNER JOIN
    nuevo_dni x1
ON
    x1.[DNI ORIGEN] = x0.[RUT EJECUTIVO]
"""

# Execute SQL Task 'Contenedor de secuencias 1\UPDATE': 3 sentencias
# separadas por 'GO' -- cruza basev2_temp con Sup_temp/Esp_temp para
# completar DNI SUPERVISOR/DNI ESPECIALISTA, y copia RUT EJECUTIVO a COD_DNI.
SQL_COMPLETAR_DNI_SUP_ESP_COD: tuple[str, ...] = (
    "UPDATE \n\tx0\nSET \n\tx0.[DNI SUPERVISOR] = x1.DNI\nFROM \n"
    "\t[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0\nINNER JOIN\n"
    "\t[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Sup_temp] x1\nON \n\tx1.SUPERVISOR = x0.SUPERVISOR",
    "UPDATE \n\tx0\nSET \n\tx0.[DNI ESPECIALISTA] = x1.DNI\nFROM \n"
    "\t[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0\nINNER JOIN\n"
    "\t[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Esp_temp] x1\nON \n\tx1.Especialista = x0.Especialista",
    "UPDATE \n\tx0\nSET \n\tx0.[COD_DNI] = x0.[RUT EJECUTIVO]\nFROM \n\t[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0",
)

# Tareas 'LOCAL' (delete-then-reinsert de TBL_FUNNEL_VENTAS2 usando
# TBL_FUNNEL_VENTAS_Temp como staging). El parametro '?' es la variable de
# paquete 'User::Fecha' (ver config.py / main.py --fecha).
SQL_LOCAL_DELETE_TEMP_MENOR_A_FECHA = "DELETE FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Temp]\nWHERE [FECHA DE EVALUACION] <  ?"
SQL_LOCAL_DELETE_VENTAS2_MAYOR_IGUAL_FECHA = "DELETE FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS2]\nWHERE [FECHA DE EVALUACION] >=  ?"
SQL_LOCAL_INSERT_VENTAS2 = "INSERT INTO [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS2]\nSELECT \n* \nFROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Temp]"
