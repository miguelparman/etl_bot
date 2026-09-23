-- Capa SILVER de la estructura medallion (ver src/correos/silver/cargar.py):
-- mismas columnas que la capa bronze TBL_CORREO_REGISTRO (ver
-- 01_bronze.sql) + columnas derivadas. La llena main.py (etapa silver) leyendo bronze, nunca los .xlsx directamente.
--
-- Usa IF OBJECT_ID(...) IS NULL (nunca DROP): 172.17.0.162 es el servidor
-- real -- volver a correrlo no toca la tabla ni sus datos.

USE [CL_MOVIL];
GO

IF OBJECT_ID('dbo.TBL_CORREO_REGISTRO_SILVER', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TBL_CORREO_REGISTRO_SILVER (
        Bandeja                          NVARCHAR(255)  NULL,
        Tipo                              NVARCHAR(20)   NULL,
        FechaHora_UTC_Texto               DATETIME2(7)   NULL,  -- campo de control de periodo, igual que en bronze
        FechaHora                        DATETIME2(7)   NULL,
        Contacto                          NVARCHAR(MAX)  NULL,
        Asunto                            NVARCHAR(MAX)  NULL,
        ID_Mensaje                        NVARCHAR(200)  NULL,
        ConversationID                    NVARCHAR(200)  NULL,
        Asesor                            NVARCHAR(200)  NULL,
        ORIGEN                            NVARCHAR(400)  NULL,
        ASUNTO_AGRUPADO                   NVARCHAR(50)   NULL   -- REBOTE / PRESENTACIÓN / PRUEBA / PROMO; NULL si ninguna regla calza (ver silver/mappings.REGLAS_ASUNTO_AGRUPADO)
    );

    CREATE INDEX IX_TBL_CORREO_REGISTRO_SILVER_FechaHoraUTC ON dbo.TBL_CORREO_REGISTRO_SILVER (FechaHora_UTC_Texto);
END
GO

-- Migracion: la primera version de silver copiaba de bronze los calculos de
-- la macro del Excel (EsPrimeraEntrada, TieneRespuesta, Tiempo_*_Horas,
-- Estado). No son confiables: se quitan de silver y quedan solo en bronze
-- (ver silver/mappings.COLUMNAS_EXCLUIDAS_SILVER).
IF COL_LENGTH('dbo.TBL_CORREO_REGISTRO_SILVER', 'EsPrimeraEntrada') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO_SILVER DROP COLUMN EsPrimeraEntrada;
IF COL_LENGTH('dbo.TBL_CORREO_REGISTRO_SILVER', 'TieneRespuesta') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO_SILVER DROP COLUMN TieneRespuesta;
IF COL_LENGTH('dbo.TBL_CORREO_REGISTRO_SILVER', 'Tiempo_Primera_Respuesta_Horas') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO_SILVER DROP COLUMN Tiempo_Primera_Respuesta_Horas;
IF COL_LENGTH('dbo.TBL_CORREO_REGISTRO_SILVER', 'Estado') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO_SILVER DROP COLUMN Estado;
IF COL_LENGTH('dbo.TBL_CORREO_REGISTRO_SILVER', 'Tiempo_Respuesta_Horas') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO_SILVER DROP COLUMN Tiempo_Respuesta_Horas;
GO
