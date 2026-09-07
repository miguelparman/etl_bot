-- Origen SSIS: OLE DB Source "TBL_ISN_CALIDAD (local)" dentro del Data Flow Task
-- "TBL_ISN_ENVIOS_CONSOLIDADOS" (AccessMode=0, modo tabla -> equivalente a SELECT * de la tabla).
-- Conexion original: 162.CL_ISN
-- Las 31 columnas pasan por el componente "Conversion de datos" (ver
-- src/transform/type_casts.py) antes de insertarse en CL_CALIDAD.dbo.TBL_ISN_ENVIOS_CONSOLIDADO.
SELECT
	[FECHA_EVENTO]
    ,[HORA_EVENTO]
    ,[ANI_EVENTO]
    ,[ANI_CONTACTO]
    ,[ID_PROVEEDOR]
    ,[ENCUESTA]
    ,[NEGOCIO]
    ,[PROCESO_NIVEL1]
    ,[PROCESO_NIVEL2]
    ,[PROCESO_NIVEL3]
    ,[PROCESO_NIVEL4]
    ,[PROCESO_NIVEL5]
    ,[EMPRESA]
    ,[ZONA]
    ,[REGION]
    ,[COMUNA]
    ,[AGENCIA]
    ,[SUBSEGMENTO]
    ,[TIPO_CONTRATO]
    ,[PRODUCTO]
    ,[TECNOLOGIA]
    ,[RUT_CLIENTE]
    ,[NOMBRE_CLIENTE]
    ,[RUT_EJECUTIVO]
    ,[NOMBRE_EJECUTIVO]
    ,[RUT_TECNICO]
    ,[NOMBRE_TECNICO]
    ,[PCRC]
    ,[BASE]
    ,[Número del caso]
    ,[REFERIDO]
FROM
	[CL_ISN].[dbo].[TBL_ISN_CALIDAD]
