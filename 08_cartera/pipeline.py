"""Orquestador del pipeline de Cartera.

Migracion de CL_Proc_Carga_Cartera.dtsx. Llama en orden a las 4 capas del
proceso -- extraccion/, validacion/, transformacion/ y carga/ -- no conoce
pyodbc, pandas.read_excel concreto ni ningun otro detalle de db.py/spreadsheet.py.

Control Flow original (3 Sequence Containers encadenados "On Success", sin
ramas condicionales ni expresiones -- ver el analisis del .dtsx para el
detalle completo):

    CARGA CARTERA TEMPORAL  -->  CARGA CARTERA ACTUAL  -->  HISTORICO CARTERA

      CARGA CARTERA TEMPORAL:
        TRUNCA TABLA -> Data Flow 'CL_TEMPORALES TBL_CARTERA' -> CARGA DNI -> VALIDA

      CARGA CARTERA ACTUAL:
        TRUNCA TABLA -> Data Flow 'ALIMENTA TABLA'

      HISTORICO CARTERA:
        ACTUALIZA STATUS TEMP CARTERA -> LIMITA CLIENTES -> LIMPIA TEMPORAL -> CARGA
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from carga import loader
from db import DatabaseGateway
from exceptions import PipelineError
from extraccion import extractor
from models import Periodo, ResultadoPipeline
from spreadsheet import SpreadsheetReader
from transformacion import transformer
from validacion import validator

logger = logging.getLogger("cartera")


@dataclass
class CarteraPipeline:
    """Orquesta el pipeline completo: extraccion -> validacion ->
    transformacion -> carga."""

    name = "cartera"

    db_cartera: DatabaseGateway
    db_temporales: DatabaseGateway
    spreadsheet_reader: SpreadsheetReader
    excel_path: Path

    def run(self, periodo: Periodo) -> ResultadoPipeline:
        logger.info("[Cartera] Inicio del pipeline (periodo=%s)", periodo)

        df_extraido = self._step(
            "CARGA CARTERA TEMPORAL / extraccion Excel",
            lambda: extractor.extraer(self.spreadsheet_reader, self.excel_path, periodo),
        )

        self._step("CARGA CARTERA TEMPORAL / TRUNCA TABLA", lambda: loader.truncar_staging(self.db_temporales))
        filas_staging = self._step(
            "CARGA CARTERA TEMPORAL / Data Flow 'CL_TEMPORALES TBL_CARTERA'",
            lambda: loader.cargar_staging(self.db_temporales, df_extraido),
        )
        self._step(
            "CARGA CARTERA TEMPORAL / CARGA DNI",
            lambda: transformer.enriquecer_con_asesores(self.db_temporales),
        )
        self._step(
            "CARGA CARTERA TEMPORAL / VALIDA",
            lambda: validator.validar_cartera_temporal(self.db_temporales),
        )

        self._step("CARGA CARTERA ACTUAL / TRUNCA TABLA", lambda: loader.truncar_actual(self.db_cartera))
        filas_actual = self._step(
            "CARGA CARTERA ACTUAL / Data Flow 'ALIMENTA TABLA'",
            lambda: loader.copiar_temporal_a_actual(self.db_temporales, self.db_cartera),
        )

        self._step(
            "HISTORICO CARTERA / ACTUALIZA STATUS TEMP CARTERA",
            lambda: transformer.actualizar_status_historico(self.db_cartera),
        )
        self._step(
            "HISTORICO CARTERA / LIMITA CLIENTES",
            lambda: transformer.limitar_clientes_historico(self.db_cartera, periodo.fecha_inicio),
        )
        self._step(
            "HISTORICO CARTERA / LIMPIA TEMPORAL",
            lambda: transformer.limpiar_temporal(self.db_cartera),
        )
        self._step(
            "HISTORICO CARTERA / CARGA",
            lambda: loader.insertar_historico(self.db_cartera),
        )

        resultado = ResultadoPipeline(
            periodo=periodo,
            filas_extraidas=len(df_extraido),
            filas_staging=filas_staging,
            filas_actual=filas_actual,
            filas_historico_insertadas=filas_staging,
        )
        logger.info("[Cartera] Pipeline finalizado correctamente: %s", resultado)
        return resultado

    def _step(self, description: str, action: Callable):
        logger.info("[Cartera] %s", description)
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - se re-lanza tipado como PipelineError
            raise PipelineError(self.name, description, exc) from exc
