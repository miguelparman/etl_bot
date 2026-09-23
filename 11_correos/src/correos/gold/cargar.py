"""Capa GOLD de la estructura medallion: modelo estrella en el esquema
'gold' (DDL en infra/sql/03_gold.sql, T-SQL de carga en sql.py),
construido desde silver (dbo.TBL_CORREO_REGISTRO_SILVER) y
dbo.TBL_CORREO_BANDEJAS.

- Dimensiones: nunca se truncan -- se agregan los valores nuevos y, en
  DIM_BANDEJA, se sobrescriben los atributos que cambian (asesor,
  coordinador, ultima revision; sin historial). Asi las claves son estables
  y los hechos de otros periodos siguen apuntando bien.
- FACT_MENSAJE: por periodo (DELETE + INSERT del rango sobre FECHA_HORA_UTC,
  mismo criterio que bronze/silver) o completa (TRUNCATE + INSERT de todo
  silver).
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from comun.logging_setup import NOMBRE_LOGGER
from gold import sql
from gold.mappings import (
    ESQUEMA_GOLD,
    TABLA_DIM_ASUNTO_AGRUPADO,
    TABLA_DIM_BANDEJA,
    TABLA_DIM_FECHA,
    TABLA_DIM_TIPO,
    TABLA_FACT_MENSAJE,
)
from silver.mappings import REGLAS_ASUNTO_AGRUPADO

logger = logging.getLogger(NOMBRE_LOGGER)


def _rango_calendario(desde: date, hasta: date) -> tuple[date, date]:
    """Se completa siempre por anios enteros (mas comodo para filtros de
    reportes que un calendario que empieza/termina donde hay datos)."""
    return date(desde.year, 1, 1), date(hasta.year, 12, 31)


def _como_fecha(valor) -> date:
    return valor.date() if isinstance(valor, datetime) else date.fromisoformat(str(valor)[:10])


def actualizar_dimensiones(gateway, periodo: tuple[datetime, datetime] | None) -> None:
    """Completa/actualiza todas las dimensiones que necesita la carga de
    hechos. 'periodo' None = todo silver (para el calendario)."""
    rango = gateway.fetch_dataframe(sql.rango_fechas_local(con_periodo=periodo is not None), periodo)
    if not rango.empty and rango.iloc[0]["DESDE"] is not None and rango.iloc[0]["HASTA"] is not None:
        desde, hasta = _rango_calendario(_como_fecha(rango.iloc[0]["DESDE"]), _como_fecha(rango.iloc[0]["HASTA"]))
        nuevas = gateway.execute_script_rowcount(sql.COMPLETAR_DIM_FECHA, (desde, hasta))
        logger.info("%s: %s fecha(s) nuevas (calendario %s a %s).", TABLA_DIM_FECHA, nuevas, desde, hasta)

    nuevas = gateway.execute_script_rowcount(sql.COMPLETAR_DIM_TIPO)
    logger.info("%s: %s tipo(s) nuevos.", TABLA_DIM_TIPO, nuevas)

    grupos = [grupo for grupo, _, _ in REGLAS_ASUNTO_AGRUPADO]
    nuevas = gateway.execute_script_rowcount(sql.completar_dim_asunto(len(grupos)), grupos)
    logger.info("%s: %s grupo(s) nuevos.", TABLA_DIM_ASUNTO_AGRUPADO, nuevas)

    afectadas = gateway.execute_script_rowcount(sql.MERGE_DIM_BANDEJA)
    logger.info("%s: %s bandeja(s) insertadas/actualizadas.", TABLA_DIM_BANDEJA, afectadas)


def cargar_periodo_gold(gateway, fecha_inicio: datetime, fecha_fin: datetime) -> tuple[int, int]:
    """Dimensiones + FACT_MENSAJE del periodo [fecha_inicio, fecha_fin).
    Devuelve (filas_eliminadas, filas_insertadas) de la tabla de hechos."""
    periodo = (fecha_inicio, fecha_fin)
    actualizar_dimensiones(gateway, periodo)

    eliminadas = gateway.execute_script_rowcount(sql.DELETE_FACT_PERIODO, periodo)
    logger.info("%s fila(s) eliminadas de %s para el periodo.", eliminadas, sql.FACT)
    insertadas = gateway.execute_script_rowcount(sql.insert_fact(con_periodo=True), periodo)
    logger.info("%s fila(s) insertadas en %s.", insertadas, sql.FACT)
    return eliminadas, insertadas


def recargar_gold_completo(gateway) -> int:
    """Dimensiones + FACT_MENSAJE completa desde todo silver (carga inicial,
    o tras reconstruir silver). Las dimensiones NO se truncan."""
    actualizar_dimensiones(gateway, None)

    gateway.truncate_table(TABLA_FACT_MENSAJE, schema=ESQUEMA_GOLD)
    insertadas = gateway.execute_script_rowcount(sql.insert_fact(con_periodo=False))
    logger.info("%s fila(s) insertadas en %s (completo).", insertadas, sql.FACT)
    return insertadas


def validar(gateway, periodo: tuple[datetime, datetime] | None) -> bool:
    """Chequeo posterior a la carga: la tabla de hechos debe tener las mismas
    filas que silver (en el periodo, o en total si 'periodo' es None) y
    ninguna sin bandeja/tipo (clave 0). Registra el resultado; devuelve True
    si todo cuadra."""
    params = tuple(periodo) * 3 if periodo is not None else None
    fila = gateway.fetch_dataframe(sql.validar(con_periodo=periodo is not None), params).iloc[0]
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
