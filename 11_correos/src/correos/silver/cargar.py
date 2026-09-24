"""Capa SILVER de la estructura medallion de 11_correos:

- Bronze: TBL_CORREO_REGISTRO -- los 'Registro' de los .xlsx tal cual (+ ORIGEN),
  cargada por bronze/cargar.py.
- Silver (se construye LEYENDO bronze, nunca los .xlsx):
  - TBL_CORREO_REGISTRO_SILVER: sin las columnas calculadas por el Excel que
    no son confiables (silver/mappings.COLUMNAS_EXCLUIDAS_SILVER), y con
    columnas derivadas: ASUNTO_AGRUPADO (ver
    silver/mappings.REGLAS_ASUNTO_AGRUPADO) y COORDINADOR.
  - TBL_CORREO_BANDEJAS_SILVER: TBL_CORREO_BANDEJAS + COORDINADOR.
- Gold: modelo estrella en el esquema 'gold', lee SOLO de silver -- ver
  gold/cargar.py.

Registro: misma estrategia de carga que bronze, por periodo (DELETE + INSERT
del rango sobre FechaHora_UTC_Texto), o completa (TRUNCATE + INSERT de todo
bronze) para la carga inicial / una reconstruccion. Bandejas: siempre
completa, igual que en bronze.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime

import pandas as pd

from bronze.mappings import COLUMNA_CONTROL_FECHA, COLUMNA_ORIGEN, TABLA_BANDEJAS, TABLA_REGISTRO
from bronze.mappings import ESQUEMA as ESQUEMA_BRONZE
from comun.logging_setup import NOMBRE_LOGGER
from silver.mappings import (
    COLUMNA_ASUNTO_AGRUPADO,
    COLUMNA_COORDINADOR,
    COLUMNAS_BANDEJAS_SILVER_DESDE_BRONZE,
    COLUMNAS_SILVER_DESDE_BRONZE,
    ESQUEMA,
    REGLAS_ASUNTO_AGRUPADO,
    TABLA_BANDEJAS_SILVER,
    TABLA_REGISTRO_SILVER,
)

_PREFIJO_ORIGEN = "registro_"

logger = logging.getLogger(NOMBRE_LOGGER)


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes ('Presentación' -> 'presentacion'), para que
    las reglas no dependan de como se escribio el asunto."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return sin_tildes.casefold()


def _patron(textos: list[str], palabra_completa: bool) -> re.Pattern[str]:
    """Una regex por regla. Con palabra_completa, el texto no puede tener una
    letra/digito pegado antes ni despues ('presentacion' calza en
    '[Presentación]' pero no en 'representación')."""
    alternativas = "|".join(re.escape(_normalizar(t)) for t in textos)
    if palabra_completa:
        return re.compile(rf"(?<!\w)(?:{alternativas})(?!\w)")
    return re.compile(alternativas)


_REGLAS_COMPILADAS = [
    (grupo, _patron(textos, palabra_completa)) for grupo, textos, palabra_completa in REGLAS_ASUNTO_AGRUPADO
]


def agrupar_asunto(asunto: object) -> str | None:
    """Devuelve el grupo de la primera regla cuyo texto aparece en 'asunto',
    o None si ninguna calza (o el asunto esta vacio)."""
    if not isinstance(asunto, str) or not asunto.strip():
        return None
    normalizado = _normalizar(asunto)
    for grupo, patron in _REGLAS_COMPILADAS:
        if patron.search(normalizado):
            return grupo
    return None


def coordinador_desde_origen(origen: object) -> str | None:
    """Nombre del coordinador a partir del nombre del .xlsx: sin el prefijo
    'Registro_' (sin distinguir mayusculas), sin extension y con '_' -> ' '.
    'Registro_JHON_MORALES_PENA.xlsx' -> 'JHON MORALES PENA'. None si vacio."""
    if not isinstance(origen, str) or not origen.strip():
        return None
    nombre = origen.strip()
    if nombre.casefold().startswith(_PREFIJO_ORIGEN):
        nombre = nombre[len(_PREFIJO_ORIGEN) :]
    if "." in nombre:
        nombre = nombre.rsplit(".", 1)[0]
    nombre = nombre.replace("_", " ").strip()
    return nombre or None


def construir_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    df = bronze_df.copy()
    df[COLUMNA_ASUNTO_AGRUPADO] = df["Asunto"].map(agrupar_asunto)
    df[COLUMNA_COORDINADOR] = df[COLUMNA_ORIGEN].map(coordinador_desde_origen)
    return df


def construir_bandejas_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    df = bronze_df.copy()
    df[COLUMNA_COORDINADOR] = df[COLUMNA_ORIGEN].map(coordinador_desde_origen)
    return df


def _select_bronze(con_periodo: bool) -> str:
    columnas_sql = ", ".join(f"[{c}]" for c in COLUMNAS_SILVER_DESDE_BRONZE)
    sql = f"SELECT {columnas_sql} FROM [{ESQUEMA_BRONZE}].[{TABLA_REGISTRO}]"
    if con_periodo:
        sql += f" WHERE [{COLUMNA_CONTROL_FECHA}] >= ? AND [{COLUMNA_CONTROL_FECHA}] < ?"
    return sql


def _log_reparto(silver_df: pd.DataFrame) -> None:
    reparto = silver_df[COLUMNA_ASUNTO_AGRUPADO].fillna("(sin grupo)").value_counts()
    for grupo, cantidad in reparto.items():
        logger.info("  %s = %s: %s fila(s)", COLUMNA_ASUNTO_AGRUPADO, grupo, cantidad)


def cargar_periodo_silver(gateway, fecha_inicio: datetime, fecha_fin: datetime) -> tuple[int, int]:
    """Reconstruye en silver solo el periodo [fecha_inicio, fecha_fin) desde
    bronze. Devuelve (filas_eliminadas, filas_insertadas)."""
    bronze_df = gateway.fetch_dataframe(_select_bronze(con_periodo=True), (fecha_inicio, fecha_fin))
    logger.info(
        "%s fila(s) leidas de [%s].[%s] (bronze) para el periodo [%s, %s).",
        len(bronze_df),
        ESQUEMA_BRONZE,
        TABLA_REGISTRO,
        fecha_inicio,
        fecha_fin,
    )
    silver_df = construir_silver(bronze_df)
    _log_reparto(silver_df)

    eliminadas = gateway.execute_script_rowcount(
        f"DELETE FROM [{ESQUEMA}].[{TABLA_REGISTRO_SILVER}] "
        f"WHERE [{COLUMNA_CONTROL_FECHA}] >= ? AND [{COLUMNA_CONTROL_FECHA}] < ?",
        (fecha_inicio, fecha_fin),
    )
    logger.info("%s fila(s) eliminadas de [%s].[%s] para el periodo.", eliminadas, ESQUEMA, TABLA_REGISTRO_SILVER)
    insertadas = gateway.bulk_insert(TABLA_REGISTRO_SILVER, silver_df, schema=ESQUEMA)
    return eliminadas, insertadas


def recargar_silver_completo(gateway) -> int:
    """Reconstruye silver completa desde TODO bronze (carga inicial, o tras
    cambiar las reglas). Devuelve filas insertadas."""
    bronze_df = gateway.fetch_dataframe(_select_bronze(con_periodo=False))
    logger.info("%s fila(s) leidas de [%s].[%s] (bronze, completo).", len(bronze_df), ESQUEMA_BRONZE, TABLA_REGISTRO)
    silver_df = construir_silver(bronze_df)
    _log_reparto(silver_df)

    gateway.truncate_table(TABLA_REGISTRO_SILVER, schema=ESQUEMA)
    return gateway.bulk_insert(TABLA_REGISTRO_SILVER, silver_df, schema=ESQUEMA)


def cargar_bandejas_silver(gateway) -> int:
    """TBL_CORREO_BANDEJAS (bronze) -> TBL_CORREO_BANDEJAS_SILVER, siempre
    completa: bronze tambien la reemplaza entera en cada corrida (es el
    estado actual de cada bandeja, no tiene periodo). Devuelve filas
    insertadas."""
    columnas_sql = ", ".join(f"[{c}]" for c in COLUMNAS_BANDEJAS_SILVER_DESDE_BRONZE)
    bronze_df = gateway.fetch_dataframe(f"SELECT {columnas_sql} FROM [{ESQUEMA_BRONZE}].[{TABLA_BANDEJAS}]")
    logger.info("%s fila(s) leidas de [%s].[%s] (bronze).", len(bronze_df), ESQUEMA_BRONZE, TABLA_BANDEJAS)
    silver_df = construir_bandejas_silver(bronze_df)

    gateway.truncate_table(TABLA_BANDEJAS_SILVER, schema=ESQUEMA)
    return gateway.bulk_insert(TABLA_BANDEJAS_SILVER, silver_df, schema=ESQUEMA)
