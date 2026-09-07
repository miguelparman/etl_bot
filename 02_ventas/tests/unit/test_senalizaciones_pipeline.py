from pathlib import Path

import pandas as pd

from etl_chile.application.use_cases.senalizaciones_pipeline import SenalizacionesPipeline
from tests.unit.fakes import (
    FakeCsvDownloader,
    FakeDatabaseGateway,
    FakeFlatFileReader,
    FakeSpreadsheetReader,
)

SENALIZACIONES_CSV_COLUMNS = [
    "Marca temporal", "Tu DNI", "Coordinador", "Rut de la Empresa", "Nombre Empresa",
    "Correo de la Empresa", "Servicio", "Sub Servicio ", "Comentario de venta",
    "Canal por donde ingresa la venta", "Mes", "OBS", "Motivo de Cancelacion",
    "Estado de Negociacion", "Fecha de Gestion del BO", "BO responsable del Caso",
    "BAM", "VOZ", "TV", "BAF", "STB", "Segmento", "Agente",
    "La señalización fue Proactiva o Reactiva", "Número del cual llama",
    "Observacion de Señalizacion", "Cantidad de líneas a contratar",
    "Teléfono de contacto", "OBSERVACION BO", "3ER CONTACTO", "2DO CONTACTO",
    "1ER CONTACTO", "DIRECCION", "COMUNA", "REGION",
]


def _build_pipeline():
    db = FakeDatabaseGateway()
    csv_df = pd.DataFrame([["x"] * len(SENALIZACIONES_CSV_COLUMNS)], columns=SENALIZACIONES_CSV_COLUMNS)
    flat_file_reader = FakeFlatFileReader(csv_df)
    dni_sheet = pd.DataFrame(
        {"DNI ORIGEN": ["1"], "DNI A CAMBIAR": ["001"], "Observación": ["obs"]}
    )
    spreadsheet_reader = FakeSpreadsheetReader({"DNI Senalizaciones$": dni_sheet})
    csv_downloader = FakeCsvDownloader()

    pipeline = SenalizacionesPipeline(
        db=db,
        flat_file_reader=flat_file_reader,
        spreadsheet_reader=spreadsheet_reader,
        csv_downloader=csv_downloader,
        senalizaciones_csv_path=Path("Señalizaciones.csv"),
        base_carta_meta_xlsx_path=Path("Base Carta Meta.xlsx"),
    )
    return pipeline, db, csv_downloader


def test_senalizaciones_pipeline_runs_all_steps_in_order():
    pipeline, db, csv_downloader = _build_pipeline()

    pipeline.run()

    assert csv_downloader.download_called is True
    assert "TBL_FUNNEL_SENHALIZACIONES" in db.truncated_tables
    assert "TBL_FUNNEL_SENHALIZACIONES" in db.inserted
    assert "TBL_FUNNEL_SENHALIZACIONES_DNI" in db.truncated_tables
    assert "TBL_FUNNEL_SENHALIZACIONES_DNI" in db.inserted
    assert any("SP_FUNNEL_SENHALIZACIONES" in s for s in db.executed_sql)
    assert len(db.executed_batches) == 1
    assert len(db.executed_batches[0]) == 19  # 18 fixups distintos + 1 duplicado original
