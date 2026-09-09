"""Orquestador del pipeline de Cartera.

Migracion de CL_Proc_Carga_Cartera.dtsx. Llama en orden a los componentes de
extraction.py, validation.py, transformation.py y load.py -- no conoce
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

import load
import transformation
import validation
from db import DatabaseGateway
from exceptions import PipelineError
from extraction import CarteraExcelExtractor
from models import Periodo, ResultadoPipeline
from spreadsheet import SpreadsheetReader

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
        extractor = CarteraExcelExtractor(self.spreadsheet_reader, self.excel_path)

        df_extraido = self._step(
            "CARGA CARTERA TEMPORAL / extraccion Excel",
            lambda: extractor.extraer(periodo),
        )

        self._step("CARGA CARTERA TEMPORAL / TRUNCA TABLA", lambda: load.truncar_staging(self.db_temporales))
        filas_staging = self._step(
            "CARGA CARTERA TEMPORAL / Data Flow 'CL_TEMPORALES TBL_CARTERA'",
            lambda: load.cargar_staging(self.db_temporales, df_extraido),
        )
        self._step(
            "CARGA CARTERA TEMPORAL / CARGA DNI",
            lambda: transformation.enriquecer_con_asesores(self.db_temporales),
        )
        self._step(
            "CARGA CARTERA TEMPORAL / VALIDA",
            lambda: validation.validar_cartera_temporal(self.db_temporales),
        )

        self._step("CARGA CARTERA ACTUAL / TRUNCA TABLA", lambda: load.truncar_actual(self.db_cartera))
        filas_actual = self._step(
            "CARGA CARTERA ACTUAL / Data Flow 'ALIMENTA TABLA'",
            lambda: load.copiar_temporal_a_actual(self.db_temporales, self.db_cartera),
        )

        self._step(
            "HISTORICO CARTERA / ACTUALIZA STATUS TEMP CARTERA",
            lambda: transformation.actualizar_status_historico(self.db_cartera),
        )
        self._step(
            "HISTORICO CARTERA / LIMITA CLIENTES",
            lambda: transformation.limitar_clientes_historico(self.db_cartera, periodo.fecha_inicio),
        )
        self._step(
            "HISTORICO CARTERA / LIMPIA TEMPORAL",
            lambda: transformation.limpiar_temporal(self.db_cartera),
        )
        self._step(
            "HISTORICO CARTERA / CARGA",
            lambda: load.insertar_historico(self.db_cartera),
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
