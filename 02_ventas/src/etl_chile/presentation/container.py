"""Composition root: crea la configuracion, los adaptadores de infraestructura
y ensambla los casos de uso (pipelines) con sus dependencias inyectadas.

Este es el UNICO lugar del proyecto donde las capas application/domain se
acoplan a implementaciones concretas de infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from etl_chile.application.use_cases.senalizaciones_pipeline import SenalizacionesPipeline
from etl_chile.application.use_cases.ventas_pipeline import VentasPipeline
from etl_chile.config.settings import Settings
from etl_chile.infrastructure.db.sqlserver_engine import create_sqlserver_engine
from etl_chile.infrastructure.db.sqlserver_gateway import SqlServerGateway
from etl_chile.infrastructure.external.google_sheets_csv_downloader import (
    GoogleSheetsCsvDownloader,
)
from etl_chile.infrastructure.files.pandas_excel_reader import PandasExcelReader
from etl_chile.infrastructure.files.pandas_flat_file_reader import PandasFlatFileReader


@dataclass
class Container:
    settings: Settings
    senalizaciones_pipeline: SenalizacionesPipeline
    ventas_pipeline: VentasPipeline

    @classmethod
    def build(cls, settings: Settings | None = None) -> "Container":
        settings = settings or Settings.from_env()

        engine = create_sqlserver_engine(settings.database)
        db = SqlServerGateway(engine)
        excel_reader = PandasExcelReader()
        flat_file_reader = PandasFlatFileReader()
        csv_downloader = GoogleSheetsCsvDownloader(
            export_url=settings.google_sheet.csv_export_url,
            destination_path=settings.paths.senalizaciones_csv,
            num_columns=settings.google_sheet.num_columns,
        )

        senalizaciones_pipeline = SenalizacionesPipeline(
            db=db,
            flat_file_reader=flat_file_reader,
            spreadsheet_reader=excel_reader,
            csv_downloader=csv_downloader,
            senalizaciones_csv_path=settings.paths.senalizaciones_csv,
            base_carta_meta_xlsx_path=settings.paths.base_carta_meta_xlsx,
        )

        ventas_pipeline = VentasPipeline(
            db=db,
            spreadsheet_reader=excel_reader,
            base_carta_meta_xlsx_path=settings.paths.base_carta_meta_xlsx,
            funnel_ventas_v2_xlsx_path=settings.paths.funnel_ventas_v2_xlsx,
        )

        return cls(
            settings=settings,
            senalizaciones_pipeline=senalizaciones_pipeline,
            ventas_pipeline=ventas_pipeline,
        )
