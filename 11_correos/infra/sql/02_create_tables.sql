-- Esquema PROVISIONAL: estas tablas no existian en CL_MOVIL (confirmado con
-- el usuario). Los tipos son una estimacion razonable basada en los datos
-- reales de los 'Registro_*.xlsx' consolidados por cargar_correos.py (ver
-- consolidar.py/mappings.py) -- no en INFORMATION_SCHEMA contra el servidor
-- real, porque 172.17.0.162 no fue alcanzable desde el entorno de
-- desarrollo. Usa IF OBJECT_ID(...) IS NULL (nunca DROP): 172.17.0.162 es
-- el servidor real, no uno de pruebas -- si ya corriste este script antes,
-- volver a correrlo no toca las tablas ni sus datos.
--
-- Ejecutar UNA VEZ contra CL_MOVIL antes de la primera corrida de
-- cargar_correos.py. Si algun tipo real difiere (ej. un NVARCHAR mas corto,
-- o 'Estado' resulta ser otra cosa cuando haya datos reales), ajustar aqui.

USE [CL_MOVIL];
GO

IF OBJECT_ID('dbo.TBL_CORREO_REGISTRO', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TBL_CORREO_REGISTRO (
        Bandeja                          NVARCHAR(255)  NULL,
        Tipo                              NVARCHAR(20)   NULL,  -- 'Entrada' / 'Salida'
        FechaHora_UTC_Texto               DATETIME2(7)   NULL,  -- convertido desde texto ISO-8601 UTC; campo de control de periodo (ver cargar_correos.py)
        FechaHora                        DATETIME2(7)   NULL,  -- convertido desde serial de Excel, hora LOCAL Peru/Bogota (UTC-5)
        Contacto                          NVARCHAR(MAX)  NULL,  -- puede traer varias direcciones separadas por ';', no un solo correo
        Asunto                            NVARCHAR(MAX)  NULL,
        ID_Mensaje                        NVARCHAR(200)  NULL,
        ConversationID                    NVARCHAR(200)  NULL,
        Asesor                            NVARCHAR(200)  NULL,
        EsPrimeraEntrada                  BIT            NULL,
        TieneRespuesta                    BIT            NULL,
        Tiempo_Primera_Respuesta_Horas    FLOAT          NULL,
        Estado                            NVARCHAR(50)   NULL,  -- siempre NULL en los datos vistos hasta ahora; se deja como texto por flexibilidad
        Tiempo_Respuesta_Horas            FLOAT          NULL,
        ORIGEN                            NVARCHAR(400)  NULL   -- nombre del .xlsx de '14 CORREOS' del que proviene la fila (400 = limite de SharePoint)
    );

    -- Soporta el DELETE/INSERT por rango de FechaHora_UTC_Texto (ver cargar_correos.cargar()).
    CREATE INDEX IX_TBL_CORREO_REGISTRO_FechaHoraUTC ON dbo.TBL_CORREO_REGISTRO (FechaHora_UTC_Texto);
END
GO

-- Migracion: la primera version de este script creo 'Contacto' como
-- NVARCHAR(255); datos reales mostraron varias direcciones separadas por
-- ';' superando ese ancho. Ensancha en vez de truncar (ver
-- [[feedback_widen_column_over_truncate]]) -- ALTER COLUMN al mismo tipo es
-- inofensivo si la tabla ya se creo con NVARCHAR(MAX).
IF OBJECT_ID('dbo.TBL_CORREO_REGISTRO', 'U') IS NOT NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO ALTER COLUMN Contacto NVARCHAR(MAX) NULL;
GO

-- Migracion: agrega 'ORIGEN' (nombre del .xlsx de origen de cada fila) a una
-- tabla creada antes de que existiera. Las filas ya cargadas quedan en NULL
-- hasta que se recargue su periodo.
IF OBJECT_ID('dbo.TBL_CORREO_REGISTRO', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.TBL_CORREO_REGISTRO', 'ORIGEN') IS NULL
    ALTER TABLE dbo.TBL_CORREO_REGISTRO ADD ORIGEN NVARCHAR(400) NULL;
GO

IF OBJECT_ID('dbo.TBL_CORREO_BANDEJAS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TBL_CORREO_BANDEJAS (
        Correo_Bandeja           NVARCHAR(255)  NULL,
        Asesor                    NVARCHAR(200)  NULL,
        UltimaRevisionEntrada     DATETIME2(7)   NULL,
        UltimaRevisionSalida      DATETIME2(7)   NULL,
        ORIGEN                    NVARCHAR(400)  NULL   -- nombre del .xlsx de '14 CORREOS' del que proviene la fila
    );
END
GO

-- Migracion: agrega 'ORIGEN' a una tabla creada antes de que existiera. Como
-- TBL_CORREO_BANDEJAS se reemplaza completa en cada carga, queda poblada en
-- la siguiente corrida.
IF OBJECT_ID('dbo.TBL_CORREO_BANDEJAS', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.TBL_CORREO_BANDEJAS', 'ORIGEN') IS NULL
    ALTER TABLE dbo.TBL_CORREO_BANDEJAS ADD ORIGEN NVARCHAR(400) NULL;
GO
