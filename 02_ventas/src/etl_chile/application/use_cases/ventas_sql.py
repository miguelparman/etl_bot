"""Sentencias SQL literales del paquete CROSS 0102 SSIS_CL_Ventas.dtsx.

Cada tupla de sentencias corresponde a un Execute SQL Task cuyo
SqlStatementSource original contenia varios batches separados por 'GO'
(eliminados aqui; cada sentencia se ejecuta por separado, ver
DatabaseGateway.execute_batch).
"""

# --- Contenedor de secuencias 2 / COMISIONES ---
TRUNCATE_RANGO_COMISIONES = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_VENTAS_RANGO_COMISIONES]"

# --- Contenedor de secuencias 2 / METAS ---
TRUNCATE_METAS_COMISIONES = "TRUNCATE TABLE METAS_COMISIONES"

# --- Contenedor de secuencias 1 / BaseV2 ---
TRUNCATE_BASEV2_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]"

# Task "Tarea Ejecutar SQL": limpieza y normalizacion de BaseV2.
CLEAN_BASEV2_TEMP: tuple[str, ...] = (
    "DELETE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] "
    "WHERE [Fecha Ingreso] is null",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] "
    "SET [RUT EJECUTIVO] = TRIM([RUT EJECUTIVO])",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] "
    "SET ESTADO = UPPER(TRIM(ESTADO))",
    "UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] "
    "SET [Rut Empresa] = LEFT(TRIM(REPLACE([Rut Empresa],'-','')),LEN([Rut Empresa]) - 2) "
    "WHERE LEN([Rut Empresa])>2",
    """UPDATE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp]
SET [FECHA DE EVALUACION] =
						CASE
							WHEN ESTADO = 'TERMINADO' AND [FECHA HABILITACION] IS NOT NULL THEN CAST([FECHA HABILITACION] AS date)
							ELSE CAST([Fecha Ingreso] AS date)
						END""",
)

# Task "update DNI": corrige RUT EJECUTIVO usando el catalogo de señalizaciones.
UPDATE_BASEV2_DNI_FROM_CATALOG = """
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

# --- Contenedor de secuencias 1 / Contenedor de secuencias (Esp) ---
TRUNCATE_ESP_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Esp_temp]"

# --- Contenedor de secuencias 1 / Sup ---
TRUNCATE_SUP_TEMP = "TRUNCATE TABLE [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Sup_temp]"

# --- Contenedor de secuencias 1 / UPDATE (fan-in: espera BaseV2, Esp y Sup) ---
FAN_IN_UPDATE_BASEV2: tuple[str, ...] = (
    """UPDATE
	x0
SET
	x0.[DNI SUPERVISOR] = x1.DNI
FROM
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0
INNER JOIN
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Sup_temp] x1
ON
	x1.SUPERVISOR = x0.SUPERVISOR""",
    """UPDATE
	x0
SET
	x0.[DNI ESPECIALISTA] = x1.DNI
FROM
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0
INNER JOIN
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Esp_temp] x1
ON
	x1.Especialista = x0.Especialista""",
    """UPDATE
	x0
SET
	x0.[COD_DNI] = x0.[RUT EJECUTIVO]
FROM
	[CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_basev2_temp] x0""",
)

# --- LOCAL ---
TRUNCATE_FUNNEL_VENTAS_TEMP = "TRUNCATE TABLE [dbo].TBL_FUNNEL_VENTAS_Temp"

DELETE_VENTAS2_FROM_FECHA = """
DELETE FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS2]
WHERE [FECHA DE EVALUACION] >=  :fecha
"""

DELETE_TEMP_BEFORE_FECHA = """
DELETE FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Temp]
WHERE [FECHA DE EVALUACION] <  :fecha
"""

INSERT_VENTAS2_FROM_TEMP = """
INSERT INTO [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS2]
SELECT
*
FROM [CL_USUARIOS].[dbo].[TBL_FUNNEL_VENTAS_Temp]
"""
