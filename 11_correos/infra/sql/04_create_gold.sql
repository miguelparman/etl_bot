-- Capa GOLD de la estructura medallion (ver src/correos/gold.py): modelo
-- estrella en el esquema [gold], construido desde silver
-- (dbo.TBL_CORREO_REGISTRO_SILVER) y dbo.TBL_CORREO_BANDEJAS.
--
--   gold.FACT_MENSAJE          1 fila por mensaje (grano: ID_MENSAJE)
--   gold.DIM_FECHA             calendario (fecha LOCAL Peru/Bogota)
--   gold.DIM_BANDEJA           bandeja + asesor + coordinador (1:1 bandeja-asesor)
--   gold.DIM_TIPO              Entrada / Salida
--   gold.DIM_ASUNTO_AGRUPADO   REBOTE / PRESENTACIÓN / PRUEBA / PROMO
--
-- Cada dimension (salvo DIM_FECHA) tiene un miembro de clave 0 con
-- descripcion vacia: la fila de hechos cuyo valor en silver es NULL apunta
-- ahi, asi las claves foraneas nunca quedan NULL.
--
-- Usa IF ... IS NULL (nunca DROP): 172.17.0.162 es el servidor real --
-- volver a correrlo no toca tablas ni datos existentes.

USE [CL_MOVIL];
GO

IF SCHEMA_ID('gold') IS NULL
    EXEC('CREATE SCHEMA gold');
GO

IF OBJECT_ID('gold.DIM_FECHA', 'U') IS NULL
    CREATE TABLE gold.DIM_FECHA (
        FECHA_KEY          INT            NOT NULL CONSTRAINT PK_DIM_FECHA PRIMARY KEY,  -- AAAAMMDD
        FECHA              DATE           NOT NULL CONSTRAINT UQ_DIM_FECHA_FECHA UNIQUE,
        ANIO               SMALLINT       NOT NULL,
        TRIMESTRE          TINYINT        NOT NULL,
        MES                TINYINT        NOT NULL,
        NOMBRE_MES         NVARCHAR(15)   NOT NULL,
        ANIO_MES           CHAR(7)        NOT NULL,  -- 'AAAA-MM'
        DIA                TINYINT        NOT NULL,
        DIA_SEMANA         TINYINT        NOT NULL,  -- 1 = lunes ... 7 = domingo
        NOMBRE_DIA         NVARCHAR(10)   NOT NULL,
        SEMANA_ISO         TINYINT        NOT NULL,
        ES_FIN_DE_SEMANA   BIT            NOT NULL
    );
GO

IF OBJECT_ID('gold.DIM_BANDEJA', 'U') IS NULL
    CREATE TABLE gold.DIM_BANDEJA (
        BANDEJA_KEY                  INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DIM_BANDEJA PRIMARY KEY,
        BANDEJA                      NVARCHAR(255)  NOT NULL CONSTRAINT UQ_DIM_BANDEJA_BANDEJA UNIQUE,
        ASESOR                       NVARCHAR(200)  NULL,
        COORDINADOR                  NVARCHAR(400)  NULL,  -- nombre del .xlsx sin 'Registro_' ni extension, '_' -> ' '
        ORIGEN                       NVARCHAR(400)  NULL,
        ULTIMA_REVISION_ENTRADA_UTC  DATETIME2(0)   NULL,  -- estado actual, desde dbo.TBL_CORREO_BANDEJAS
        ULTIMA_REVISION_SALIDA_UTC   DATETIME2(0)   NULL
    );
GO

IF OBJECT_ID('gold.DIM_TIPO', 'U') IS NULL
    CREATE TABLE gold.DIM_TIPO (
        TIPO_KEY  INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DIM_TIPO PRIMARY KEY,
        TIPO      NVARCHAR(20)   NOT NULL CONSTRAINT UQ_DIM_TIPO_TIPO UNIQUE
    );
GO

IF OBJECT_ID('gold.DIM_ASUNTO_AGRUPADO', 'U') IS NULL
    CREATE TABLE gold.DIM_ASUNTO_AGRUPADO (
        ASUNTO_AGRUPADO_KEY  INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DIM_ASUNTO_AGRUPADO PRIMARY KEY,
        ASUNTO_AGRUPADO      NVARCHAR(50)   NOT NULL CONSTRAINT UQ_DIM_ASUNTO_AGRUPADO UNIQUE
    );
GO

-- Miembros de clave 0 (descripcion vacia) para valores NULL en silver.
IF NOT EXISTS (SELECT 1 FROM gold.DIM_BANDEJA WHERE BANDEJA_KEY = 0)
BEGIN
    SET IDENTITY_INSERT gold.DIM_BANDEJA ON;
    INSERT INTO gold.DIM_BANDEJA (BANDEJA_KEY, BANDEJA) VALUES (0, N'');
    SET IDENTITY_INSERT gold.DIM_BANDEJA OFF;
END
GO
IF NOT EXISTS (SELECT 1 FROM gold.DIM_TIPO WHERE TIPO_KEY = 0)
BEGIN
    SET IDENTITY_INSERT gold.DIM_TIPO ON;
    INSERT INTO gold.DIM_TIPO (TIPO_KEY, TIPO) VALUES (0, N'');
    SET IDENTITY_INSERT gold.DIM_TIPO OFF;
END
GO
IF NOT EXISTS (SELECT 1 FROM gold.DIM_ASUNTO_AGRUPADO WHERE ASUNTO_AGRUPADO_KEY = 0)
BEGIN
    SET IDENTITY_INSERT gold.DIM_ASUNTO_AGRUPADO ON;
    INSERT INTO gold.DIM_ASUNTO_AGRUPADO (ASUNTO_AGRUPADO_KEY, ASUNTO_AGRUPADO) VALUES (0, N'');
    SET IDENTITY_INSERT gold.DIM_ASUNTO_AGRUPADO OFF;
END
GO

IF OBJECT_ID('gold.FACT_MENSAJE', 'U') IS NULL
BEGIN
    CREATE TABLE gold.FACT_MENSAJE (
        MENSAJE_KEY          BIGINT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_FACT_MENSAJE PRIMARY KEY,
        FECHA_KEY            INT            NOT NULL CONSTRAINT FK_FACT_MENSAJE_FECHA REFERENCES gold.DIM_FECHA (FECHA_KEY),
        HORA_LOCAL           TINYINT        NOT NULL,  -- 0..23, hora local Peru/Bogota
        BANDEJA_KEY          INT            NOT NULL CONSTRAINT FK_FACT_MENSAJE_BANDEJA REFERENCES gold.DIM_BANDEJA (BANDEJA_KEY),
        TIPO_KEY             INT            NOT NULL CONSTRAINT FK_FACT_MENSAJE_TIPO REFERENCES gold.DIM_TIPO (TIPO_KEY),
        ASUNTO_AGRUPADO_KEY  INT            NOT NULL CONSTRAINT FK_FACT_MENSAJE_ASUNTO REFERENCES gold.DIM_ASUNTO_AGRUPADO (ASUNTO_AGRUPADO_KEY),
        ID_MENSAJE           NVARCHAR(200)  NULL,
        CONVERSATION_ID      NVARCHAR(200)  NULL,
        ASUNTO               NVARCHAR(MAX)  NULL,
        CONTACTO             NVARCHAR(MAX)  NULL,
        FECHA_HORA_UTC       DATETIME2(7)   NOT NULL,  -- campo de control de periodo, misma precision que silver (el DELETE por rango debe coincidir exacto)
        FECHA_HORA_LOCAL     DATETIME2(0)   NOT NULL,
        CANTIDAD             INT            NOT NULL CONSTRAINT DF_FACT_MENSAJE_CANTIDAD DEFAULT (1)
    );

    CREATE INDEX IX_FACT_MENSAJE_FECHA_HORA_UTC ON gold.FACT_MENSAJE (FECHA_HORA_UTC);
    CREATE INDEX IX_FACT_MENSAJE_FECHA_KEY ON gold.FACT_MENSAJE (FECHA_KEY);
    CREATE INDEX IX_FACT_MENSAJE_BANDEJA_KEY ON gold.FACT_MENSAJE (BANDEJA_KEY);
END
GO
