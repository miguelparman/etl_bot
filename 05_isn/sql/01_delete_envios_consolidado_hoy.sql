-- Origen SSIS: Execute SQL Task "DELETE ENVIOS_CONSOLIDADO (LOCAL)"
-- Reutilizado dos veces en el paquete original:
--   1) Al inicio del "Contenedor de secuencias" (limpieza preventiva)
--   2) Al inicio de "ACTUALIZACION SERVIDOR" dentro de TBL_ISN_CALIDAD
-- Conexion original: 162.CL_CALIDAD
DELETE [CL_CALIDAD].[dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]
WHERE [FECHA DE CARGA] = CAST(GETDATE() AS date)
