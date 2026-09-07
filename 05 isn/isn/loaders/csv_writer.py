"""
Reemplaza:
- Microsoft.FlatFileDestination "Destino de archivo plano" del Data Flow
  'TBL_ISN\\EXPORT CSV' (conexión "CSV" -> isn.csv): delimitado por ';',
  sin calificador de texto, CodePage 1252, con encabezado, sobrescribe.
- Microsoft.FileSystemTask "Cambiar nombre archivo": copia isn.csv al
  archivo con fecha en la carpeta 'Automatizado' (ver ISN_ARCHIVE_OPERATION
  en config.py sobre la ambigüedad Copy/Move del original).
"""
from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from config import settings
from isn.columns import COLUMNAS_EXPORT_ISN

logger = logging.getLogger(__name__)


def exportar_isn_csv(df: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or settings.csv_isn_path
    path.parent.mkdir(parents=True, exist_ok=True)
    faltantes = [c for c in COLUMNAS_EXPORT_ISN if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas para exportar a {path}: {faltantes}")
    logger.info("Exportando %d filas a %s", len(df), path)
    df[COLUMNAS_EXPORT_ISN].to_csv(
        path,
        sep=";",
        index=False,
        encoding=settings.csv_isn_encoding,
        lineterminator="\r\n",
    )
    return path


def archivar_isn_csv(origen: Path | None = None) -> Path:
    """Tarea 'Cambiar nombre archivo': User::New_name_file se recalcula con
    la fecha de hoy, igual que la expresión original (GETDATE())."""
    origen = origen or settings.csv_isn_path
    settings.isn_archive_dir.mkdir(parents=True, exist_ok=True)
    destino = settings.isn_archive_dir / f"PROSPECTOS_EMPRESA_{date.today():%Y%m%d}.csv"

    if settings.isn_archive_operation == "move":
        logger.info("Moviendo %s -> %s", origen, destino)
        shutil.move(str(origen), str(destino))
    else:
        logger.info("Copiando %s -> %s", origen, destino)
        shutil.copy2(str(origen), str(destino))
    return destino
