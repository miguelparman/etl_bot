-- Log de ejecuciones del ETL (ver src/correos/comun/ejecucion.py): una fila
-- por corrida de main.py. main.py la abre al empezar (ESTADO = 'EN_CURSO')
-- y la cierra al terminar (OK / ERROR). gold.FACT_MENSAJE.ID_EJECUCION
-- apunta aqui.
--
-- En dbo (no en gold): es informacion de operacion, no del modelo de
-- reportes. Correr DESPUES de 03_gold.sql (agrega la FK desde FACT_MENSAJE).
--
-- Usa IF ... IS NULL (nunca DROP): 172.17.0.162 es el servidor real --
-- volver a correrlo no toca la tabla ni sus datos.

USE [CL_MOVIL];
GO

IF OBJECT_ID('dbo.TBL_CORREO_LOG_EJECUCION', 'U') IS NULL
    CREATE TABLE dbo.TBL_CORREO_LOG_EJECUCION (
        ID_EJECUCION     BIGINT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_TBL_CORREO_LOG_EJECUCION PRIMARY KEY,
        FECHA_INICIO     DATETIME2(0)   NOT NULL,  -- hora local Peru/Bogota
        FECHA_FIN        DATETIME2(0)   NULL,      -- hora local Peru/Bogota; NULL mientras corre
        ESTADO           NVARCHAR(20)   NOT NULL,  -- EN_CURSO / OK / ERROR
        ETAPAS           NVARCHAR(100)  NOT NULL,  -- ej. 'ingesta -> bronze -> silver -> gold'
        MODO             NVARCHAR(20)   NOT NULL,  -- periodo / completo
        PERIODO_INICIO   DATETIME2(0)   NULL,      -- UTC, inclusivo (NULL en modo completo)
        PERIODO_FIN      DATETIME2(0)   NULL,      -- UTC, exclusivo
        FILAS_BRONZE     INT            NULL,      -- filas insertadas en TBL_CORREO_REGISTRO (NULL si la etapa no corrio)
        FILAS_SILVER     INT            NULL,      -- filas insertadas en TBL_CORREO_REGISTRO_SILVER
        FILAS_GOLD       INT            NULL,      -- filas insertadas en gold.FACT_MENSAJE
        VALIDACION_GOLD  NVARCHAR(20)   NULL,      -- OK / NO CUADRA
        MENSAJE_ERROR    NVARCHAR(MAX)  NULL,
        USUARIO          NVARCHAR(128)  NULL,
        EQUIPO           NVARCHAR(128)  NULL
    );
GO

IF OBJECT_ID('gold.FK_FACT_MENSAJE_EJECUCION', 'F') IS NULL
   AND COL_LENGTH('gold.FACT_MENSAJE', 'ID_EJECUCION') IS NOT NULL
    ALTER TABLE gold.FACT_MENSAJE
        ADD CONSTRAINT FK_FACT_MENSAJE_EJECUCION FOREIGN KEY (ID_EJECUCION)
        REFERENCES dbo.TBL_CORREO_LOG_EJECUCION (ID_EJECUCION);
GO
