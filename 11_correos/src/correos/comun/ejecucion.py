"""Log de ejecuciones del ETL (dbo.TBL_CORREO_LOG_EJECUCION, DDL en
infra/sql/04_log_ejecucion.sql): una fila por corrida de main.py.

main.py abre la fila al empezar (ESTADO = 'EN_CURSO') y obtiene su
ID_EJECUCION, que gold graba en cada fila de FACT_MENSAJE; al terminar la
cierra con el estado final, las filas por etapa y la validacion de gold.
Fechas en hora local Peru/Bogota (ver periodo.ahora_local); el periodo, en
UTC como en el resto del proceso."""

from __future__ import annotations

import getpass
import logging
import socket
from dataclasses import dataclass
from datetime import datetime

from comun.logging_setup import NOMBRE_LOGGER
from comun.periodo import ahora_local

logger = logging.getLogger(NOMBRE_LOGGER)

TABLA_LOG = "[dbo].[TBL_CORREO_LOG_EJECUCION]"

ESTADO_EN_CURSO = "EN_CURSO"
ESTADO_OK = "OK"
ESTADO_ERROR = "ERROR"


@dataclass(frozen=True)
class Ejecucion:
    id_ejecucion: int
    # Inicio de la corrida (hora local). Es tambien FECHA_CARGA de todas las
    # filas que inserta esta corrida: un mismo valor por carga.
    fecha_carga: datetime


@dataclass
class ResultadoEjecucion:
    """Lo que se registra al cerrar la fila del log (None = etapa no corrio)."""

    filas_bronze: int | None = None
    filas_silver: int | None = None
    filas_gold: int | None = None
    validacion_gold: str | None = None  # 'OK' / 'NO CUADRA'


SQL_INICIAR = f"""
INSERT INTO {TABLA_LOG} (FECHA_INICIO, ESTADO, ETAPAS, MODO, PERIODO_INICIO, PERIODO_FIN, USUARIO, EQUIPO)
OUTPUT INSERTED.ID_EJECUCION
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

SQL_FINALIZAR = f"""
UPDATE {TABLA_LOG}
SET FECHA_FIN = ?, ESTADO = ?, FILAS_BRONZE = ?, FILAS_SILVER = ?, FILAS_GOLD = ?,
    VALIDACION_GOLD = ?, MENSAJE_ERROR = ?
WHERE ID_EJECUCION = ?
"""


def _identidad() -> tuple[str | None, str | None]:
    """Usuario y equipo que corren el proceso (informativo; None si no se
    pueden obtener)."""
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = None
    try:
        equipo = socket.gethostname()
    except Exception:
        equipo = None
    return usuario, equipo


def iniciar_ejecucion(
    gateway, etapas: list[str], completo: bool, periodo: tuple[datetime, datetime] | None
) -> Ejecucion:
    """Abre la fila del log con ESTADO = 'EN_CURSO' y devuelve su id."""
    inicio = ahora_local()
    usuario, equipo = _identidad()
    id_ejecucion = gateway.insert_returning_id(
        SQL_INICIAR,
        (
            inicio,
            ESTADO_EN_CURSO,
            " -> ".join(etapas),
            "completo" if completo else "periodo",
            periodo[0] if periodo else None,
            periodo[1] if periodo else None,
            usuario,
            equipo,
        ),
    )
    logger.info("Ejecucion %s iniciada (%s).", id_ejecucion, inicio)
    return Ejecucion(id_ejecucion=id_ejecucion, fecha_carga=inicio)


def finalizar_ejecucion(
    gateway, ejecucion: Ejecucion, estado: str, resultado: ResultadoEjecucion, mensaje_error: str | None = None
) -> None:
    """Cierra la fila del log. Nunca levanta: si el log falla (p.ej. se
    cayo la conexion) solo se registra, para no tapar el error original."""
    try:
        gateway.execute_script_rowcount(
            SQL_FINALIZAR,
            (
                ahora_local(),
                estado,
                resultado.filas_bronze,
                resultado.filas_silver,
                resultado.filas_gold,
                resultado.validacion_gold,
                mensaje_error,
                ejecucion.id_ejecucion,
            ),
        )
        logger.info("Ejecucion %s finalizada: %s.", ejecucion.id_ejecucion, estado)
    except Exception as exc:
        logger.error("No se pudo cerrar la ejecucion %s en el log: %s", ejecucion.id_ejecucion, exc)
