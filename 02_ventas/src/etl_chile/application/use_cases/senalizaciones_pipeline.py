"""Caso de uso: pipeline de Señalizaciones.

Port de CROSS 0101 SSIS_CL_Senalizaciones.dtsx.

Orden de ejecucion original (Control Flow, todas las precedencias son
"On Success"):

    Descargar googledrive señalizaciones (Execute Process)
      -> TRUNCATE SEÑALIZACIONES
      -> TBL_FUNNEL_SENHALIZACIONES (Data Flow)
      -> SP_FUNNEL_SENHALIZACIONES
      -> UPDATE (correcciones literales de DNI)
      -> [Contenedor de secuencias]
            TRUNCATE (TBL_FUNNEL_SENHALIZACIONES_DNI)
            -> TBL_FUNNEL_SENHALIZACIONES_DNI (Data Flow)
            -> UPDATE (correccion de DNI via catalogo)
"""

from __future__ import annotations

import logging
from pathlib import Path

from etl_chile.application.ports.csv_downloader import CsvDownloader
from etl_chile.application.ports.database_gateway import DatabaseGateway
from etl_chile.application.ports.flat_file_reader import FlatFileReader
from etl_chile.application.ports.spreadsheet_reader import SpreadsheetReader
from etl_chile.application.use_cases import senalizaciones_sql as sql
from etl_chile.application.use_cases.column_transform import apply_column_spec
from etl_chile.application.use_cases.dni_senalizaciones_sync import sync_dni_senalizaciones
from etl_chile.application.use_cases.senalizaciones_mappings import (
    FUNNEL_SENALIZACIONES_COLUMN_SPEC,
    FUNNEL_SENALIZACIONES_TABLE,
    SENALIZACIONES_RAW_CSV_COLUMNS,
)
from etl_chile.domain.exceptions import PipelineError

logger = logging.getLogger(__name__)


class SenalizacionesPipeline:
    """Orquesta el pipeline completo de Señalizaciones."""

    name = "senalizaciones"

    def __init__(
        self,
        db: DatabaseGateway,
        flat_file_reader: FlatFileReader,
        spreadsheet_reader: SpreadsheetReader,
        csv_downloader: CsvDownloader,
        senalizaciones_csv_path: Path,
        base_carta_meta_xlsx_path: Path,
    ) -> None:
        self._db = db
        self._flat_file_reader = flat_file_reader
        self._spreadsheet_reader = spreadsheet_reader
        self._csv_downloader = csv_downloader
        self._senalizaciones_csv_path = senalizaciones_csv_path
        self._base_carta_meta_xlsx_path = base_carta_meta_xlsx_path

    def run(self) -> None:
        logger.info("[Señalizaciones] Inicio del pipeline")
        self._step("descargar CSV de Google Sheets", self._download_csv)
        self._step("truncar TBL_FUNNEL_SENHALIZACIONES", self._truncate_funnel)
        self._step("cargar funnel de señalizaciones", self._load_funnel)
        self._step("ejecutar SP_FUNNEL_SENHALIZACIONES", self._exec_stored_procedure)
        self._step("aplicar correcciones literales de DNI", self._apply_literal_dni_fixups)
        self._step("sincronizar catalogo de DNI", self._sync_dni_catalog)
        self._step("aplicar correccion de DNI via catalogo", self._apply_dni_catalog_update)
        logger.info("[Señalizaciones] Pipeline finalizado correctamente")

    def _step(self, description: str, action) -> None:
        logger.info("[Señalizaciones] %s", description)
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - se re-lanza tipado como PipelineError
            raise PipelineError(self.name, description, exc) from exc

    def _download_csv(self) -> None:
        self._csv_downloader.download()

    def _truncate_funnel(self) -> None:
        self._db.truncate_table(FUNNEL_SENALIZACIONES_TABLE)

    def _load_funnel(self) -> None:
        raw = self._flat_file_reader.read_csv(
            self._senalizaciones_csv_path, column_names=SENALIZACIONES_RAW_CSV_COLUMNS
        )
        transformed = apply_column_spec(raw, FUNNEL_SENALIZACIONES_COLUMN_SPEC)
        self._db.bulk_insert(FUNNEL_SENALIZACIONES_TABLE, transformed)

    def _exec_stored_procedure(self) -> None:
        self._db.execute(sql.EXEC_SP_FUNNEL_SENHALIZACIONES)

    def _apply_literal_dni_fixups(self) -> None:
        self._db.execute_batch(sql.DNI_LITERAL_FIXUPS)

    def _sync_dni_catalog(self) -> None:
        sync_dni_senalizaciones(
            self._db, self._spreadsheet_reader, self._base_carta_meta_xlsx_path
        )

    def _apply_dni_catalog_update(self) -> None:
        self._db.execute(sql.UPDATE_DNI_FROM_CATALOG)
