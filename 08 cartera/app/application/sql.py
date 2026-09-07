"""Sentencias T-SQL migradas literalmente desde los Execute SQL Task de
CL_Proc_Carga_Cartera.dtsx. Sin cambios de negocio salvo lo indicado en cada
comentario (y en el README, seccion "Notas de fidelidad").

Cada constante corresponde a UNA tarea del Control Flow original; se ejecuta
como un unico script (sin separadores 'GO', que el paquete original tampoco
usaba) para que las variables locales T-SQL (p.ej. @FECHA_INICIO) conserven
su alcance entre sentencias.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Sequence "CARGA CARTERA TEMPORAL"
# ---------------------------------------------------------------------------

TRUNCATE_STAGING = "TRUNCATE TABLE [CL_TEMPORALES].[dbo].[TBL_CARTERA]"

# Tarea 'CARGA DNI': enriquece TBL_CARTERA con datos de asesor/ejecutivo
# desde CL_DATA.dbo.TBL_PLACES (maestro, cross-database, solo lectura).
#
# NOTA DE FIDELIDAD: se conserva tal cual un defecto preexistente del
# paquete original -- la rama ELSE de 'RUT_SMTRDV' reasigna
# 'X0.[RUT_SMTRIO]' en lugar de 'X0.[RUT_SMTRDV]'. No se corrige porque no
# fue solicitado explicitamente.
ENRIQUECER_CON_ASESORES = """
UPDATE X0
SET
 [RUT_SM] = CASE WHEN X1.[Rut] IS NOT NULL THEN REPLACE(X1.Rut,'-','') ELSE REPLACE(X0.[RUT_SMDV],'-','') END
,[RUT_SMDV] = CASE WHEN X1.[Rut] IS NOT NULL THEN X1.Rut ELSE X0.[RUT_SMDV] END
,[NOM_SM] = CASE WHEN X1.[Asesor] IS NOT NULL THEN UPPER(X1.[Asesor]) ELSE X0.[NOM_SM] END
,[RUT_SMDUP] = CASE WHEN X2.[Rut] IS NOT NULL THEN REPLACE(X2.Rut,'-','') ELSE REPLACE(X0.[RUT_SMDUP],'-','') END
,[RUT_SMDUDV] = CASE WHEN X2.[Rut] IS NOT NULL THEN X2.Rut ELSE X0.[RUT_SMDUDV] END
,[NOM_SMDUP] = CASE WHEN X2.[Asesor] IS NOT NULL THEN UPPER(X2.[Asesor]) ELSE X0.[NOM_SMDUP] END
,[RUT_SMTRIO] = CASE WHEN X3.[Rut] IS NOT NULL THEN REPLACE(X3.Rut,'-','') ELSE REPLACE(X0.[RUT_SMTRIO],'-','') END
,[RUT_SMTRDV] = CASE WHEN X3.[Rut] IS NOT NULL THEN X3.Rut ELSE X0.[RUT_SMTRIO] END
,[NOM_SMTRI] = CASE WHEN X3.[Asesor] IS NOT NULL THEN UPPER(X3.[Asesor]) ELSE X0.[NOM_SMTRI] END
,[NOM_SUP] = CASE WHEN X4.Rut IS NOT NULL THEN UPPER(X4.[Asesor]) ELSE X0.[NOM_SUP] END
,[DNI] = X1.[DNI]
,[Etiqueta] = X1.[Etiqueta]
,[RUT_SIN_DV] = REPLACE(X0.[RUT_DV],'-','')
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] X0
LEFT JOIN [CL_DATA].[dbo].[TBL_PLACES] X1 ON X1.ID = X0.ID_GENESM
LEFT JOIN [CL_DATA].[dbo].[TBL_PLACES] X2 ON X2.ID = X0.[ID_GENDUP]
LEFT JOIN [CL_DATA].[dbo].[TBL_PLACES] X3 ON X3.ID = X0.[ID_GENTRI]
LEFT JOIN [CL_DATA].[dbo].[TBL_PLACES] X4 ON X0.RUT_SUP = X4.Rut;
"""

# Segunda sentencia de la misma tarea 'CARGA DNI' (en el .dtsx original iba a
# continuacion, dentro del mismo SqlStatementSource).
NORMALIZAR_SUB_SEGMENTO = """
UPDATE [CL_TEMPORALES].[dbo].[TBL_CARTERA]
SET SUB_SEGME = REPLACE(SUB_SEGME, 'Triadas', 'Triada')
"""

# Tarea 'VALIDA': 4 controles 'IF EXISTS (...) RAISERROR' migrados a 4
# consultas escalares (ver validation.py). Se conserva el orden y el mensaje
# original de cada uno, y el mismo comportamiento de "abortar en el primer
# fallo" (no se siguen evaluando los siguientes controles).
VALIDA_RUT_DUPLICADO = """
SELECT COUNT(*) FROM (
    SELECT [RUT_SIN_DV]
    FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA]
    GROUP BY [RUT_SIN_DV]
    HAVING COUNT(*) > 1
) duplicados
"""
MSG_RUT_DUPLICADO = "RUC DUPLICADO TBL_CARTERA_ACTUAL"

VALIDA_ASESOR_NO_ASIGNADO = (
    "SELECT COUNT(*) FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE DNI IS NULL"
)
MSG_ASESOR_NO_ASIGNADO = "ASESOR NO ASIGNADO"

VALIDA_RUT_NO_ASIGNADO = (
    "SELECT COUNT(*) FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE [RUT_SMDV] IS NULL"
)
MSG_RUT_NO_ASIGNADO = "RUT NO ASIGNADO"

VALIDA_NOMBRE_NO_ASIGNADO = (
    "SELECT COUNT(*) FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE [NOM_SM] IS NULL"
)
MSG_NOMBRE_NO_ASIGNADO = "NOMBRE NO ASIGNADO"

# ---------------------------------------------------------------------------
# Sequence "CARGA CARTERA ACTUAL"
# ---------------------------------------------------------------------------

TRUNCATE_ACTUAL = "TRUNCATE TABLE [CL_CARTERA].[dbo].[TBL_CARTERA_ACTUAL]"

# ---------------------------------------------------------------------------
# Sequence "HISTORICO CARTERA"
# ---------------------------------------------------------------------------

# Tarea 'ACTUALIZA STATUS TEMP CARTERA'. Usa tablas temporales globales
# (##...), igual que el paquete original.
ACTUALIZA_STATUS_TEMP_CARTERA = """
DROP TABLE IF EXISTS ##RUCS_DE_ULTIMA_CARTERA;
SELECT DISTINCT(RUT_SIN_DV) RUT_SIN_DV INTO ##RUCS_DE_ULTIMA_CARTERA
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA]
WHERE fecha_fin=(SELECT MAX(fecha_fin) FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA]);

DROP TABLE IF EXISTS ##TODOS_RUCS_HISTORIAL_CARTERA;
SELECT DISTINCT(RUT_SIN_DV) RUT_SIN_DV INTO ##TODOS_RUCS_HISTORIAL_CARTERA
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA];

UPDATE A SET STATUS='SE MANTIENE'
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A
WHERE RUT_SIN_DV IN (SELECT * FROM ##RUCS_DE_ULTIMA_CARTERA);

UPDATE A SET STATUS='NUEVO'
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A
WHERE STATUS IS NULL AND RUT_SIN_DV NOT IN (SELECT RUT_SIN_DV FROM ##TODOS_RUCS_HISTORIAL_CARTERA);

UPDATE A SET STATUS='REINGRESO'
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A
WHERE STATUS IS NULL;

UPDATE A SET ULTIMA_FECHA_FIN=(SELECT MAX(fecha_fin) FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] c WHERE A.RUT_SIN_DV=c.RUT_SIN_DV)
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A WHERE STATUS='REINGRESO';

UPDATE A SET ULTIMA_FECHA_INICIO=(SELECT MAX(fecha_inicio) FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] c WHERE A.RUT_SIN_DV=c.RUT_SIN_DV)
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A WHERE STATUS='REINGRESO';

UPDATE A SET A.MODIFICADO=
    CASE WHEN A.SEGME!=B.SEGME OR A.SUB_SEGME!=B.SUB_SEGME OR A.ID_GENESM!=B.ID_GENESM
         OR A.NOM_SM!=B.NOM_SM OR A.NOM_SUP!=B.NOM_SUP OR A.Etiqueta!=B.Etiqueta
         OR A.DNI != B.COD_DNI OR A.ing_sspp != B.ing_sspp
    THEN 'SI' ELSE 'NO' END
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A
LEFT JOIN [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] B
  ON A.RUT_SIN_DV=B.RUT_SIN_DV AND A.fecha_fin=B.fecha_fin
WHERE A.STATUS='SE MANTIENE';
"""

# Tarea 'LIMITA CLIENTES'. Tiene 1 parametro posicional ('?'), enlazado en el
# .dtsx original a la variable de paquete User::Fecha_Inicio.
LIMITA_CLIENTES = """
DECLARE @FECHA_INICIO INT = ?;
DECLARE @FECHA_INICIO_DATE DATE;
SET @FECHA_INICIO_DATE = CONVERT(DATE, CONVERT(CHAR(8), @FECHA_INICIO));
SET @FECHA_INICIO_DATE = DATEADD(DAY, -1, @FECHA_INICIO_DATE);
SET @FECHA_INICIO = CONVERT(INT, FORMAT(@FECHA_INICIO_DATE, 'yyyyMMdd'));

-- LOS REINGRESO
UPDATE X0
SET [fecha_fin] = @FECHA_INICIO, ESTADO = 'RETIRADO'
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] X0
LEFT JOIN [CL_TEMPORALES].[dbo].[TBL_CARTERA] X1 ON X0.RUT_SIN_DV = X1.RUT_SIN_DV
WHERE X0.[fecha_fin] = (CONVERT(VARCHAR,GETDATE(),112)) AND X1.RUT_SIN_DV IS NULL;

-- LOS MODIFICADOS
UPDATE X0
SET [fecha_fin] = @FECHA_INICIO, ESTADO = 'SE MANTIENE', MODIFICADO='SI'
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] X0
INNER JOIN (SELECT RUT_SIN_DV FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE [STATUS] = 'SE MANTIENE' AND MODIFICADO='SI') X1
  ON X0.RUT_SIN_DV = X1.RUT_SIN_DV
WHERE X0.[fecha_fin] = (CONVERT(VARCHAR,GETDATE(),112));
"""

# Tarea 'LIMPIA TEMPORAL'.
LIMPIA_TEMPORAL = """
UPDATE A SET ESTADO='SE MANTIENE', MODIFICADO='NO'
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] A
WHERE fecha_fin=(CONVERT(VARCHAR,GETDATE(),112))
  AND RUT_SIN_DV IN (SELECT RUT_SIN_DV FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE [STATUS] = 'SE MANTIENE' AND MODIFICADO='NO');

DELETE [CL_TEMPORALES].[dbo].[TBL_CARTERA]
WHERE RUT_SIN_DV IN (SELECT RUT_SIN_DV FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] WHERE [STATUS] = 'SE MANTIENE' AND MODIFICADO='NO');

UPDATE A SET A.ULTIMA_FECHA_FIN=NULL
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA] A WHERE STATUS!='REINGRESO';
"""

# Tarea 'CARGA'. INSERT posicional (sin lista de columnas, tal como en el
# .dtsx original) -- ver README, seccion "Notas de fidelidad", sobre la
# necesidad de verificar el orden real de columnas de TBL_HISTORIAL_CARTERA
# contra la base de datos antes de operar en produccion.
CARGA_HISTORICO = """
INSERT INTO [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA]
SELECT [RUT_DV],[NOMCLI],[SEGME],[SUB_SEGME],[ID_GENESM],[NOM_SM],[NOM_SUP],[fecha_inicio],[fecha_fin],
       [Etiqueta],[RUT_SIN_DV],DNI,[STATUS],RUT_SM,MODIFICADO,
       CASE WHEN STATUS = 'REINGRESO' THEN ULTIMA_FECHA_FIN ELSE NULL END,
       NULL
FROM [CL_TEMPORALES].[dbo].[TBL_CARTERA];

UPDATE X0
SET X0.ing_sspp = X1.ing_sspp
FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA] X0
LEFT JOIN [CL_CARTERA].[dbo].[TBL_CARTERA_ACTUAL] X1 ON X0.RUT_SIN_DV = X1.RUT_SIN_DV
WHERE X0.fecha_fin = (SELECT MAX(fecha_fin) FROM [CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA]);
"""
