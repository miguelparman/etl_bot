"""Equivalente al contenedor "TBL_ISN" del .dtsx original (rama paralela A):
DROP+CREATE TBL_ISN -> Data Flow "EXPORT CSV" -> File System Task
"Cambiar nombre archivo"."""
from __future__ import annotations

import logging
import shutil
from datetime import date

from sqlalchemy import Engine

from src.config.settings import FilePathSettings
from src.database.connection import execute_script
from src.extract.sql import read_query
from src.utils.audit import RunAudit

logger = logging.getLogger("ssis_cl_isn")

# Mismo formato que el Connection Manager de archivo plano "CSV" del original:
# delimitador ';', sin calificador de texto, CP1252, encabezado en la primera fila.
_CSV_SEPARATOR = ";"
_CSV_ENCODING = "cp1252"


def build_tbl_isn(engine: Engine) -> None:
    """Execute SQL Task "TBL_ISN": DROP + SELECT INTO desde TBL_ISN_PRE
    (WHERE Indice = 1), ejecutado ANTES del Data Flow de exportacion."""
    with engine.begin() as conn:
        execute_script(conn, "13_drop_tbl_isn.sql")
        execute_script(conn, "14_create_tbl_isn.sql")
    logger.info("TBL_ISN reconstruida")


def export_csv(engine: Engine, paths: FilePathSettings, audit: RunAudit) -> None:
    """Data Flow "EXPORT CSV": OLE DB Source TBL_ISN -> Flat File Destination
    isn.csv. Es un pase directo (pass-through), sin transformacion de columnas."""
    with engine.connect() as conn:
        df = read_query(conn, "15_select_tbl_isn_for_export.sql")

    audit.record_extracted("export_tbl_isn", df.height)

    destination = paths.isn_source_csv
    destination.parent.mkdir(parents=True, exist_ok=True)

    # El original tenia Overwrite=true (el archivo se recrea en cada corrida).
    df.write_csv(
        destination,
        separator=_CSV_SEPARATOR,
        include_header=True,
        quote_style="never",
    )
    _reencode_to_cp1252(destination)

    audit.record_loaded("export_tbl_isn", df.height)
    logger.info("isn.csv exportado (%s filas) en %s", df.height, destination)


def _reencode_to_cp1252(path) -> None:
    """polars.write_csv siempre escribe UTF-8; el Flat File Connection Manager
    original usaba CodePage=1252, asi que se re-codifica el archivo despues de
    escribirlo para mantener compatibilidad con el consumidor final del CSV."""
    text = path.read_text(encoding="utf-8")
    path.write_text(text, encoding=_CSV_ENCODING, errors="replace")


def archive_csv(paths: FilePathSettings, run_date: date) -> None:
    """File System Task "Cambiar nombre archivo": copia isn.csv a un nombre
    con fecha (equivalente a la expresion de User::New_name_file).

    Operation por defecto del FileSystemTask original = copiar (no hay
    atributo "Operation" en el .dtsx, TaskOverwriteDestFile=True), por lo que
    isn.csv NO se mueve/borra: queda intacto para la siguiente corrida.
    """
    source = paths.isn_source_csv
    destination = paths.dated_archive_csv(run_date)
    shutil.copy2(source, destination)
    logger.info("Archivo archivado: %s -> %s", source, destination)
