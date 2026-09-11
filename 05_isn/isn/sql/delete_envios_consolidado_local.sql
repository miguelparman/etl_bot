-- Tarea 'DELETE ENVIOS_CONSOLIDADO (LOCAL)', conexión 162.CL_ISN.
-- NOTA: hace lo mismo que delete_envios_consolidado_calidad.sql (sección
-- ACTUALIZACION SERVIDOR) pero cruzando de base desde CL_ISN -- se preserva
-- la duplicación tal cual está en el .dtsx original.
DELETE [CL_CALIDAD].[dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]
WHERE [FECHA DE CARGA] = CAST(GETDATE() AS date)
