"""Capa GOLD de la estructura medallion: modelo estrella en el esquema
'gold' (DDL en infra/sql/04_create_gold.sql), construido desde silver
(dbo.TBL_CORREO_REGISTRO_SILVER) y dbo.TBL_CORREO_BANDEJAS.

- Dimensiones: nunca se truncan -- se agregan los valores nuevos y, en
  DIM_BANDEJA, se sobrescriben los atributos que cambian (asesor,
  coordinador, ultima revision; sin historial). Asi las claves son estables
  y los hechos de otros periodos siguen apuntando bien.
- FACT_MENSAJE: por periodo (DELETE + INSERT del rango sobre FECHA_HORA_UTC,
  mismo criterio que bronze/silver) o completa (TRUNCATE + INSERT de todo
  silver).

Todo corre como T-SQL en el servidor: los cruces con las dimensiones son
set-based y no hace falta traer las filas a Python.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from logging_setup import NOMBRE_LOGGER
from mappings import (
    COLUMNA_CONTROL_FECHA,
    DESFASE_HORAS_LOCAL,
    ESQUEMA,
    ESQUEMA_GOLD,
    REGLAS_ASUNTO_AGRUPADO,
    TABLA_BANDEJAS,
    TABLA_DIM_ASUNTO_AGRUPADO,
    TABLA_DIM_BANDEJA,
    TABLA_DIM_FECHA,
    TABLA_DIM_TIPO,
    TABLA_FACT_MENSAJE,
    TABLA_REGISTRO_SILVER,
)

logger = logging.getLogger(NOMBRE_LOGGER)

_SILVER = f"[{ESQUEMA}].[{TABLA_REGISTRO_SILVER}]"
_BANDEJAS = f"[{ESQUEMA}].[{TABLA_BANDEJAS}]"
_FACT = f"[{ESQUEMA_GOLD}].[{TABLA_FACT_MENSAJE}]"
_DIM_FECHA = f"[{ESQUEMA_GOLD}].[{TABLA_DIM_FECHA}]"
_DIM_BANDEJA = f"[{ESQUEMA_GOLD}].[{TABLA_DIM_BANDEJA}]"
_DIM_TIPO = f"[{ESQUEMA_GOLD}].[{TABLA_DIM_TIPO}]"
_DIM_ASUNTO = f"[{ESQUEMA_GOLD}].[{TABLA_DIM_ASUNTO_AGRUPADO}]"

# 'FechaHora' ya viene en hora local (serial de Excel), pero con artefactos
# de redondeo (ej. 09:37:13.999999): se redondea al segundo al pasar a
# DATETIME2(0) -- si no, 23:59:59.999999 caeria en el dia anterior. Si
# faltara, se deriva de la hora UTC con el desfase fijo.
_FECHA_HORA_LOCAL = (
    f"CAST(COALESCE(s.[FechaHora], DATEADD(HOUR, {DESFASE_HORAS_LOCAL}, s.[{COLUMNA_CONTROL_FECHA}])) AS DATETIME2(0))"
)

_WHERE_PERIODO_SILVER = f"s.[{COLUMNA_CONTROL_FECHA}] >= ? AND s.[{COLUMNA_CONTROL_FECHA}] < ?"


def sql_rango_fechas_local(con_periodo: bool) -> str:
    sql = f"SELECT MIN(CAST({_FECHA_HORA_LOCAL} AS DATE)) AS DESDE, MAX(CAST({_FECHA_HORA_LOCAL} AS DATE)) AS HASTA FROM {_SILVER} s"
    if con_periodo:
        sql += f" WHERE {_WHERE_PERIODO_SILVER}"
    return sql


# Calendario: inserta solo las fechas que faltan entre dos dias. Nombres en
# espanol con CHOOSE (no depende del SET LANGUAGE del login) y dia de semana
# calculado contra 1900-01-01 (lunes), sin depender de SET DATEFIRST.
SQL_COMPLETAR_DIM_FECHA = f"""
WITH dias AS (
    SELECT CAST(? AS DATE) AS F
    UNION ALL
    SELECT DATEADD(DAY, 1, F) FROM dias WHERE F < CAST(? AS DATE)
)
INSERT INTO {_DIM_FECHA}
    (FECHA_KEY, FECHA, ANIO, TRIMESTRE, MES, NOMBRE_MES, ANIO_MES, DIA, DIA_SEMANA, NOMBRE_DIA, SEMANA_ISO, ES_FIN_DE_SEMANA)
SELECT
    CONVERT(INT, CONVERT(CHAR(8), d.F, 112)),
    d.F,
    YEAR(d.F),
    DATEPART(QUARTER, d.F),
    MONTH(d.F),
    CHOOSE(MONTH(d.F), N'Enero', N'Febrero', N'Marzo', N'Abril', N'Mayo', N'Junio', N'Julio',
           N'Agosto', N'Septiembre', N'Octubre', N'Noviembre', N'Diciembre'),
    CONVERT(CHAR(7), d.F, 126),
    DAY(d.F),
    ds.N,
    CHOOSE(ds.N, N'Lunes', N'Martes', N'Miércoles', N'Jueves', N'Viernes', N'Sábado', N'Domingo'),
    DATEPART(ISO_WEEK, d.F),
    CASE WHEN ds.N >= 6 THEN 1 ELSE 0 END
FROM dias d
CROSS APPLY (SELECT DATEDIFF(DAY, '19000101', d.F) % 7 + 1 AS N) ds
WHERE NOT EXISTS (SELECT 1 FROM {_DIM_FECHA} x WHERE x.FECHA = d.F)
OPTION (MAXRECURSION 0);
"""

SQL_COMPLETAR_DIM_TIPO = f"""
INSERT INTO {_DIM_TIPO} (TIPO)
SELECT DISTINCT s.[Tipo] FROM {_SILVER} s
WHERE s.[Tipo] IS NOT NULL AND s.[Tipo] <> N''
  AND NOT EXISTS (SELECT 1 FROM {_DIM_TIPO} d WHERE d.TIPO = s.[Tipo]);
"""


def sql_completar_dim_asunto(cantidad_reglas: int) -> str:
    """Grupos de las reglas (asi existen aunque aun no haya mensajes) + los
    que aparezcan en silver."""
    valores = ", ".join("(?)" for _ in range(cantidad_reglas))
    return f"""
INSERT INTO {_DIM_ASUNTO} (ASUNTO_AGRUPADO)
SELECT g.GRUPO FROM (
    SELECT GRUPO FROM (VALUES {valores}) AS r (GRUPO)
    UNION
    SELECT DISTINCT s.[ASUNTO_AGRUPADO] FROM {_SILVER} s WHERE s.[ASUNTO_AGRUPADO] IS NOT NULL
) g
WHERE g.GRUPO <> N'' AND NOT EXISTS (SELECT 1 FROM {_DIM_ASUNTO} d WHERE d.ASUNTO_AGRUPADO = g.GRUPO);
"""


# Origen de DIM_BANDEJA: TBL_CORREO_BANDEJAS (estado actual, preferido) +
# bandejas que solo aparecen en silver (su asesor/origen del mensaje mas
# reciente). ROW_NUMBER defensivo: el MERGE falla si una bandeja llega dos
# veces. COORDINADOR = ORIGEN sin 'Registro_' ni extension, '_' -> ' '.
SQL_MERGE_DIM_BANDEJA = f"""
WITH desde_bandejas AS (
    SELECT b.Correo_Bandeja AS BANDEJA, b.Asesor AS ASESOR, b.ORIGEN,
           b.UltimaRevisionEntrada AS ENTRADA, b.UltimaRevisionSalida AS SALIDA,
           ROW_NUMBER() OVER (PARTITION BY b.Correo_Bandeja ORDER BY b.UltimaRevisionEntrada DESC, b.ORIGEN) AS RN
    FROM {_BANDEJAS} b
    WHERE b.Correo_Bandeja IS NOT NULL AND b.Correo_Bandeja <> N''
),
desde_silver AS (
    SELECT s.[Bandeja] AS BANDEJA, s.[Asesor] AS ASESOR, s.[ORIGEN],
           CAST(NULL AS DATETIME2) AS ENTRADA, CAST(NULL AS DATETIME2) AS SALIDA,
           ROW_NUMBER() OVER (PARTITION BY s.[Bandeja] ORDER BY s.[{COLUMNA_CONTROL_FECHA}] DESC) AS RN
    FROM {_SILVER} s
    WHERE s.[Bandeja] IS NOT NULL AND s.[Bandeja] <> N''
      AND NOT EXISTS (SELECT 1 FROM {_BANDEJAS} b WHERE b.Correo_Bandeja = s.[Bandeja])
),
origen AS (
    SELECT o.BANDEJA, o.ASESOR, o.ORIGEN, o.ENTRADA, o.SALIDA,
           NULLIF(REPLACE(
               CASE WHEN CHARINDEX('.', p.SIN_PREFIJO) > 0
                    THEN LEFT(p.SIN_PREFIJO, LEN(p.SIN_PREFIJO) - CHARINDEX('.', REVERSE(p.SIN_PREFIJO)))
                    ELSE p.SIN_PREFIJO END,
               '_', ' '), N'') AS COORDINADOR
    FROM (SELECT * FROM desde_bandejas WHERE RN = 1 UNION ALL SELECT * FROM desde_silver WHERE RN = 1) o
    CROSS APPLY (SELECT CASE WHEN o.ORIGEN LIKE 'Registro[_]%' THEN STUFF(o.ORIGEN, 1, 9, N'') ELSE o.ORIGEN END AS SIN_PREFIJO) p
)
MERGE {_DIM_BANDEJA} AS d
USING origen AS o ON d.BANDEJA = o.BANDEJA
WHEN MATCHED THEN UPDATE SET
    d.ASESOR = o.ASESOR,
    d.COORDINADOR = o.COORDINADOR,
    d.ORIGEN = o.ORIGEN,
    d.ULTIMA_REVISION_ENTRADA_UTC = o.ENTRADA,
    d.ULTIMA_REVISION_SALIDA_UTC = o.SALIDA
WHEN NOT MATCHED BY TARGET THEN INSERT
    (BANDEJA, ASESOR, COORDINADOR, ORIGEN, ULTIMA_REVISION_ENTRADA_UTC, ULTIMA_REVISION_SALIDA_UTC)
    VALUES (o.BANDEJA, o.ASESOR, o.COORDINADOR, o.ORIGEN, o.ENTRADA, o.SALIDA);
"""


def sql_insert_fact(con_periodo: bool) -> str:
    """Silver -> FACT_MENSAJE. LEFT JOIN + ISNULL(..., 0): un valor NULL (o
    sin match) apunta al miembro vacio de clave 0 en vez de perder la fila."""
    sql = f"""
INSERT INTO {_FACT}
    (FECHA_KEY, HORA_LOCAL, BANDEJA_KEY, TIPO_KEY, ASUNTO_AGRUPADO_KEY,
     ID_MENSAJE, CONVERSATION_ID, ASUNTO, CONTACTO, FECHA_HORA_UTC, FECHA_HORA_LOCAL, CANTIDAD)
SELECT
    CONVERT(INT, CONVERT(CHAR(8), CAST(l.FECHA_HORA_LOCAL AS DATE), 112)),
    DATEPART(HOUR, l.FECHA_HORA_LOCAL),
    ISNULL(b.BANDEJA_KEY, 0),
    ISNULL(t.TIPO_KEY, 0),
    ISNULL(a.ASUNTO_AGRUPADO_KEY, 0),
    s.[ID_Mensaje], s.[ConversationID], s.[Asunto], s.[Contacto],
    s.[{COLUMNA_CONTROL_FECHA}], l.FECHA_HORA_LOCAL, 1
FROM {_SILVER} s
CROSS APPLY (SELECT {_FECHA_HORA_LOCAL} AS FECHA_HORA_LOCAL) l
LEFT JOIN {_DIM_BANDEJA} b ON b.BANDEJA = s.[Bandeja]
LEFT JOIN {_DIM_TIPO} t ON t.TIPO = s.[Tipo]
LEFT JOIN {_DIM_ASUNTO} a ON a.ASUNTO_AGRUPADO = s.[ASUNTO_AGRUPADO]
"""
    if con_periodo:
        sql += f"WHERE {_WHERE_PERIODO_SILVER}\n"
    return sql


SQL_DELETE_FACT_PERIODO = f"DELETE FROM {_FACT} WHERE FECHA_HORA_UTC >= ? AND FECHA_HORA_UTC < ?"


def _rango_calendario(desde: date, hasta: date) -> tuple[date, date]:
    """Se completa siempre por anios enteros (mas comodo para filtros de
    reportes que un calendario que empieza/termina donde hay datos)."""
    return date(desde.year, 1, 1), date(hasta.year, 12, 31)


def _como_fecha(valor) -> date:
    return valor.date() if isinstance(valor, datetime) else date.fromisoformat(str(valor)[:10])


def actualizar_dimensiones(gateway, periodo: tuple[datetime, datetime] | None) -> None:
    """Completa/actualiza todas las dimensiones que necesita la carga de
    hechos. 'periodo' None = todo silver (para el calendario)."""
    rango = gateway.fetch_dataframe(sql_rango_fechas_local(con_periodo=periodo is not None), periodo)
    if not rango.empty and rango.iloc[0]["DESDE"] is not None and rango.iloc[0]["HASTA"] is not None:
        desde, hasta = _rango_calendario(_como_fecha(rango.iloc[0]["DESDE"]), _como_fecha(rango.iloc[0]["HASTA"]))
        nuevas = gateway.execute_script_rowcount(SQL_COMPLETAR_DIM_FECHA, (desde, hasta))
        logger.info("%s: %s fecha(s) nuevas (calendario %s a %s).", TABLA_DIM_FECHA, nuevas, desde, hasta)

    nuevas = gateway.execute_script_rowcount(SQL_COMPLETAR_DIM_TIPO)
    logger.info("%s: %s tipo(s) nuevos.", TABLA_DIM_TIPO, nuevas)

    grupos = [grupo for grupo, _, _ in REGLAS_ASUNTO_AGRUPADO]
    nuevas = gateway.execute_script_rowcount(sql_completar_dim_asunto(len(grupos)), grupos)
    logger.info("%s: %s grupo(s) nuevos.", TABLA_DIM_ASUNTO_AGRUPADO, nuevas)

    afectadas = gateway.execute_script_rowcount(SQL_MERGE_DIM_BANDEJA)
    logger.info("%s: %s bandeja(s) insertadas/actualizadas.", TABLA_DIM_BANDEJA, afectadas)


def cargar_periodo_gold(gateway, fecha_inicio: datetime, fecha_fin: datetime) -> tuple[int, int]:
    """Dimensiones + FACT_MENSAJE del periodo [fecha_inicio, fecha_fin).
    Devuelve (filas_eliminadas, filas_insertadas) de la tabla de hechos."""
    periodo = (fecha_inicio, fecha_fin)
    actualizar_dimensiones(gateway, periodo)

    eliminadas = gateway.execute_script_rowcount(SQL_DELETE_FACT_PERIODO, periodo)
    logger.info("%s fila(s) eliminadas de %s para el periodo.", eliminadas, _FACT)
    insertadas = gateway.execute_script_rowcount(sql_insert_fact(con_periodo=True), periodo)
    logger.info("%s fila(s) insertadas en %s.", insertadas, _FACT)
    return eliminadas, insertadas


def recargar_gold_completo(gateway) -> int:
    """Dimensiones + FACT_MENSAJE completa desde todo silver (carga inicial,
    o tras reconstruir silver). Las dimensiones NO se truncan."""
    actualizar_dimensiones(gateway, None)

    gateway.truncate_table(TABLA_FACT_MENSAJE, schema=ESQUEMA_GOLD)
    insertadas = gateway.execute_script_rowcount(sql_insert_fact(con_periodo=False))
    logger.info("%s fila(s) insertadas en %s (completo).", insertadas, _FACT)
    return insertadas


def sql_validar(con_periodo: bool) -> str:
    where_silver = f" WHERE {_WHERE_PERIODO_SILVER}" if con_periodo else ""
    where_fact = " WHERE FECHA_HORA_UTC >= ? AND FECHA_HORA_UTC < ?" if con_periodo else " WHERE 1 = 1"
    return f"""
SELECT
    (SELECT COUNT(*) FROM {_SILVER} s{where_silver}) AS FILAS_SILVER,
    (SELECT COUNT(*) FROM {_FACT}{where_fact}) AS FILAS_FACT,
    (SELECT COUNT(*) FROM {_FACT}{where_fact} AND (BANDEJA_KEY = 0 OR TIPO_KEY = 0)) AS FILAS_SIN_BANDEJA_O_TIPO
"""


def validar(gateway, periodo: tuple[datetime, datetime] | None) -> bool:
    """Chequeo posterior a la carga: la tabla de hechos debe tener las mismas
    filas que silver (en el periodo, o en total si 'periodo' es None) y
    ninguna sin bandeja/tipo (clave 0). Registra el resultado; devuelve True
    si todo cuadra."""
    params = tuple(periodo) * 3 if periodo is not None else None
    fila = gateway.fetch_dataframe(sql_validar(con_periodo=periodo is not None), params).iloc[0]
    silver, fact, sin_clave = int(fila["FILAS_SILVER"]), int(fila["FILAS_FACT"]), int(fila["FILAS_SIN_BANDEJA_O_TIPO"])
    ok = silver == fact and sin_clave == 0
    registrar = logger.info if ok else logger.error
    registrar(
        "Validacion gold: silver=%s / fact=%s fila(s); %s sin bandeja o tipo -> %s.",
        silver,
        fact,
        sin_clave,
        "OK" if ok else "NO CUADRA",
    )
    return ok
