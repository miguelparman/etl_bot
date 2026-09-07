-- Crea las dos bases usadas por el paquete: CL_CAMPAÑAS (datos del proceso) y
-- CL_CARTERA (base de clientes, usada solo para el JOIN final).
IF DB_ID('CL_CAMPAÑAS') IS NULL
    CREATE DATABASE [CL_CAMPAÑAS];
GO

IF DB_ID('CL_CARTERA') IS NULL
    CREATE DATABASE [CL_CARTERA];
GO
