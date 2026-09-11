USE CL_ANALISIS;
GO

IF OBJECT_ID('dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE', 'U') IS NOT NULL
    DROP TABLE dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE;
GO

-- Esquema inferido de las External Columns del OLE DB Destination del .dtsx
-- (no se pudo consultar INFORMATION_SCHEMA.COLUMNS real -- confirmar contra
-- la base de producción antes de usar este DDL fuera del ambiente de pruebas).
CREATE TABLE dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE (
    [RUC]                         NVARCHAR(20)  NULL,
    [NOMBRE CLIENTE]              NVARCHAR(300) NULL,
    [SEGMENTO GLOBAL]             NVARCHAR(50)  NULL,
    [SUBSEGMENTO LOCAL]           NVARCHAR(30)  NULL,
    [NÚMERO DOCUMENTO]            NVARCHAR(30)  NULL,
    [NOMBRE]                      NVARCHAR(50)  NULL,
    [APELLIDOS]                   NVARCHAR(100) NULL,
    [CARGO]                       NVARCHAR(200) NULL,
    [TELÉFONO]                    NVARCHAR(20)  NULL,
    [MÓVIL]                       NVARCHAR(20)  NULL,
    [CORREO ELECTRÓNICO]          NVARCHAR(80)  NULL,
    [AUTORIZACIONES FUNCIONALES]  NVARCHAR(500) NULL,
    [ACCESO PLATINO]              INT           NULL,
    [REPRESENTANTE LEGAL]         INT           NULL,
    [FECHA CREACIÓN]              DATE          NULL,
    [FECHA MODIFICACIÓN]          DATE          NULL,
    [CREADO POR]                  NVARCHAR(80)  NULL,
    [ÚLTIMA  MODIFICACIÓN POR]    NVARCHAR(80)  NULL,
    [ID CONTACTO]                 NVARCHAR(30)  NULL
);
GO

IF OBJECT_ID('dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS', 'U') IS NOT NULL
    DROP TABLE dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS;
GO

CREATE TABLE dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS (
    [telefono] NVARCHAR(25) NULL
);
GO
