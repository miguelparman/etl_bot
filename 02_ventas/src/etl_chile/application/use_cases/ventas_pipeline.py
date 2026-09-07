"""Caso de uso: pipeline de Ventas.

Port de CROSS 0102 SSIS_CL_Ventas.dtsx.

Estructura de Control Flow original (3 contenedores raiz, en cadena "On
Success"):

    Contenedor de secuencias 2  -->  Contenedor de secuencias 1  -->  LOCAL

"Contenedor de secuencias 2" tiene 3 ramas SIN precedencia entre si
(COMISIONES, DNI Señalizaciones, METAS): se ejecutan aqui de forma
secuencial (el orden relativo entre ellas es indiferente, tal como en el
paquete original).

"Contenedor de secuencias 1" tiene 3 ramas independientes (BaseV2, Esp, Sup)
seguidas de un paso "UPDATE" que actua como fan-in (espera a que las 3
terminen).

El parametro `fecha` equivale a la variable de paquete `User::Fecha`, que en
el .dtsx original no se calculaba dentro del paquete sino que la inyectaba
el proceso/scheduler que lo invocaba (dtexec /Set ...Fecha.Value=...).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from etl_chile.application.ports.database_gateway import DatabaseGateway
from etl_chile.application.ports.spreadsheet_reader import SpreadsheetReader
from etl_chile.application.use_cases import ventas_mappings as mappings
from etl_chile.application.use_cases import ventas_sql as sql
from etl_chile.application.use_cases.column_transform import apply_column_spec
from etl_chile.application.use_cases.dni_senalizaciones_sync import sync_dni_senalizaciones
from etl_chile.domain.exceptions import PipelineError

logger = logging.getLogger(__name__)


class VentasPipeline:
    """Orquesta el pipeline completo de Ventas."""

    name = "ventas"

    def __init__(
        self,
        db: DatabaseGateway,
        spreadsheet_reader: SpreadsheetReader,
        base_carta_meta_xlsx_path: Path,
        funnel_ventas_v2_xlsx_path: Path,
    ) -> None:
        self._db = db
        self._spreadsheet_reader = spreadsheet_reader
        self._base_carta_meta_xlsx_path = base_carta_meta_xlsx_path
        self._funnel_ventas_v2_xlsx_path = funnel_ventas_v2_xlsx_path

    def run(self, fecha: date) -> None:
        logger.info("[Ventas] Inicio del pipeline (fecha de corte=%s)", fecha)

        self._step("Contenedor de secuencias 2 / COMISIONES", self._run_comisiones)
        self._step(
            "Contenedor de secuencias 2 / DNI Señalizaciones", self._run_dni_senalizaciones
        )
        self._step("Contenedor de secuencias 2 / METAS", self._run_metas)

        self._step("Contenedor de secuencias 1 / BaseV2", self._run_basev2)
        self._step("Contenedor de secuencias 1 / Esp", self._run_esp)
        self._step("Contenedor de secuencias 1 / Sup", self._run_sup)
        self._step("Contenedor de secuencias 1 / UPDATE (fan-in)", self._run_fan_in_update)

        self._step("LOCAL", lambda: self._run_local(fecha))

        logger.info("[Ventas] Pipeline finalizado correctamente")

    def _step(self, description: str, action) -> None:
        logger.info("[Ventas] %s", description)
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - se re-lanza tipado como PipelineError
            raise PipelineError(self.name, description, exc) from exc

    # ------------------------------------------------------------------
    # Contenedor de secuencias 2
    # ------------------------------------------------------------------
    def _run_comisiones(self) -> None:
        self._db.execute(sql.TRUNCATE_RANGO_COMISIONES)
        raw = self._spreadsheet_reader.read_sheet(
            self._base_carta_meta_xlsx_path, mappings.RANGO_COMISIONES_SHEET
        )
        transformed = apply_column_spec(raw, mappings.RANGO_COMISIONES_COLUMN_SPEC)
        self._db.bulk_insert(mappings.RANGO_COMISIONES_TABLE, transformed)

    def _run_dni_senalizaciones(self) -> None:
        sync_dni_senalizaciones(
            self._db, self._spreadsheet_reader, self._base_carta_meta_xlsx_path
        )

    def _run_metas(self) -> None:
        self._db.execute(sql.TRUNCATE_METAS_COMISIONES)
        raw = self._spreadsheet_reader.read_sheet(
            self._base_carta_meta_xlsx_path, mappings.METAS_COMISIONES_SHEET
        )
        transformed = apply_column_spec(raw, mappings.METAS_COMISIONES_COLUMN_SPEC)
        self._db.bulk_insert(mappings.METAS_COMISIONES_TABLE, transformed)

    # ------------------------------------------------------------------
    # Contenedor de secuencias 1
    # ------------------------------------------------------------------
    def _run_basev2(self) -> None:
        self._db.execute(sql.TRUNCATE_BASEV2_TEMP)

        raw = self._spreadsheet_reader.read_sheet(
            self._funnel_ventas_v2_xlsx_path, mappings.BASEV2_SHEET
        )
        transformed = apply_column_spec(raw, mappings.BASEV2_COLUMN_SPEC)
        self._db.bulk_insert(mappings.BASEV2_TABLE, transformed)

        self._db.execute_batch(sql.CLEAN_BASEV2_TEMP)
        self._db.execute(sql.UPDATE_BASEV2_DNI_FROM_CATALOG)

    def _run_esp(self) -> None:
        self._db.execute(sql.TRUNCATE_ESP_TEMP)
        raw = self._spreadsheet_reader.read_sheet(
            self._funnel_ventas_v2_xlsx_path, mappings.ESP_SHEET
        )
        transformed = apply_column_spec(raw, mappings.ESP_COLUMN_SPEC)
        self._db.bulk_insert(mappings.ESP_TABLE, transformed)

    def _run_sup(self) -> None:
        self._db.execute(sql.TRUNCATE_SUP_TEMP)
        raw = self._spreadsheet_reader.read_sheet(
            self._funnel_ventas_v2_xlsx_path, mappings.SUP_SHEET
        )
        transformed = apply_column_spec(raw, mappings.SUP_COLUMN_SPEC)
        self._db.bulk_insert(mappings.SUP_TABLE, transformed)

    def _run_fan_in_update(self) -> None:
        self._db.execute_batch(sql.FAN_IN_UPDATE_BASEV2)

    # ------------------------------------------------------------------
    # LOCAL
    # ------------------------------------------------------------------
    def _run_local(self, fecha: date) -> None:
        self._db.execute(sql.TRUNCATE_FUNNEL_VENTAS_TEMP)

        raw = self._db.read_table(mappings.FUNNEL_VENTAS_TEMP_SOURCE_TABLE)
        transformed = apply_column_spec(raw, mappings.FUNNEL_VENTAS_TEMP_COLUMN_SPEC)
        self._db.bulk_insert(mappings.FUNNEL_VENTAS_TEMP_TABLE, transformed)

        self._db.execute(sql.DELETE_VENTAS2_FROM_FECHA, {"fecha": fecha})
        self._db.execute(sql.DELETE_TEMP_BEFORE_FECHA, {"fecha": fecha})
        self._db.execute(sql.INSERT_VENTAS2_FROM_TEMP)
