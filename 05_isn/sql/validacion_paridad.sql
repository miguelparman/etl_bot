-- ============================================================================
-- Consultas de validacion de paridad SSIS vs Python (seccion 12 del pedido).
-- Ejecutar ANTES de apagar el paquete SSIS original: correr ambos procesos
-- (SSIS en su entorno, Python contra una copia/staging de las mismas bases)
-- para el MISMO rango de fechas y comparar los resultados de estas consultas.
-- No se ejecutan automaticamente desde main.py: son para validacion manual /
-- un job de QA aparte durante el periodo de transicion.
-- ============================================================================

-- 1) Conteo de filas de las tablas finales
SELECT 'TBL_ISN_SF' AS tabla, COUNT(*) AS filas FROM [CL_ISN].[dbo].[TBL_ISN_SF]
UNION ALL
SELECT 'TBL_ISN_PRE', COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN_PRE]
UNION ALL
SELECT 'TBL_ISN', COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN]
UNION ALL
SELECT 'TBL_ISN_CALIDAD', COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN_CALIDAD]
UNION ALL
SELECT 'TBL_ISN_ENVIOS_CONSOLIDADO (hoy)', COUNT(*)
FROM [CL_CALIDAD].[dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]
WHERE [FECHA DE CARGA] = CAST(GETDATE() AS date);

-- 2) TBL_ISN y TBL_ISN_CALIDAD deben tener EXACTAMENTE el mismo numero de filas
--    que TBL_ISN_PRE filtrado a Indice = 1 (misma proyeccion/filtro de origen)
SELECT
    (SELECT COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN_PRE] WHERE Indice = 1) AS pre_indice_1,
    (SELECT COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN])                      AS tbl_isn,
    (SELECT COUNT(*) FROM [CL_ISN].[dbo].[TBL_ISN_CALIDAD])              AS tbl_isn_calidad;

-- 3) No debe haber RUT_CLIENTE duplicado en TBL_ISN (Indice=1 ya deduplica en el origen)
SELECT RUT_CLIENTE, COUNT(*) AS ocurrencias
FROM [CL_ISN].[dbo].[TBL_ISN]
GROUP BY RUT_CLIENTE
HAVING COUNT(*) > 1;

-- 4) FECHA DE CARGA no debe quedar NULL despues del UPDATE final
SELECT COUNT(*) AS filas_sin_fecha_carga
FROM [CL_CALIDAD].[dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]
WHERE [FECHA DE CARGA] IS NULL
  AND [Número del caso] IN (
        SELECT [Número del caso] FROM [CL_ISN].[dbo].[TBL_ISN_CALIDAD]
      );

-- 5) Comparacion de totales/checksum por columna clave entre dos corridas
--    (reemplazar <TABLA_REFERENCIA_SSIS> por una copia de la tabla generada
--    por el paquete SSIS original, tomada ANTES de migrar, para diff manual)
-- SELECT CHECKSUM_AGG(CHECKSUM(*)) FROM [CL_ISN].[dbo].[TBL_ISN];
-- SELECT CHECKSUM_AGG(CHECKSUM(*)) FROM <TABLA_REFERENCIA_SSIS>;

-- 6) Valores NULL por columna en TBL_ISN (comparar el mismo perfil contra la
--    corrida de referencia de SSIS)
SELECT
    SUM(CASE WHEN RUT_CLIENTE IS NULL THEN 1 ELSE 0 END)   AS null_rut_cliente,
    SUM(CASE WHEN NOMBRE_CLIENTE IS NULL THEN 1 ELSE 0 END) AS null_nombre_cliente,
    SUM(CASE WHEN PCRC IS NULL THEN 1 ELSE 0 END)           AS null_pcrc
FROM [CL_ISN].[dbo].[TBL_ISN];
