-- Tarea original: UPDATE "_0" del paquete SSIS_CL_ISN_Contactos.dtsx.
-- Quita el sufijo ".0" que a veces queda en MÓVIL/TELÉFONO cuando el dato
-- llega como número flotante desde alguna fuente upstream (Excel/Salesforce).
UPDATE [CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE]
  SET [MÓVIL] = REPLACE([MÓVIL],'.0','')
  WHERE [MÓVIL] LIKE '%.0%'
GO

UPDATE [CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE]
  SET [TELÉFONO] = REPLACE([TELÉFONO],'.0','')
  WHERE [TELÉFONO] LIKE '%.0%'
GO
