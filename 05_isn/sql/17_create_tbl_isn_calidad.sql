-- Origen SSIS: Execute SQL Task "TBL_ISN_CALIDAD" (dentro de "TBL_ISN_CALIDAD")
-- Es la MISMA proyeccion de columnas y el MISMO filtro (Indice = 1) que 14_create_tbl_isn.sql,
-- pero materializada en una tabla distinta para la carga hacia CL_CALIDAD.
-- Conexion original: 162.CL_ISN
SELECT [FECHA_EVENTO]
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
INTO
	[CL_ISN].[dbo].[TBL_ISN_CALIDAD]
FROM
	[CL_ISN].[dbo].[TBL_ISN_PRE]
WHERE
	Indice = 1
