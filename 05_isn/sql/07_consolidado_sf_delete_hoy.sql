-- Origen SSIS: Execute SQL Task "DELETE" (dentro de "Contenedor de secuencias", en SECUENCIA NUEVA)
-- Conexion original: 162.CL_ISN
DELETE [CL_ISN].[dbo].[TBL_ISN_SF_CONSOLIDADO]
WHERE FECHA_DE_CARGA = CAST(GETDATE() AS DATE)
