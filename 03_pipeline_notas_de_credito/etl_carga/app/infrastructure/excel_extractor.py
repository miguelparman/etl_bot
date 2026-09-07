"""Adaptador de infraestructura: extracción desde el Excel de origen (NC_.xlsx).

Equivalente a la parte de lectura/tipado de ETL_NC_polars.py, que la tarea
'Tarea Ejecutar proceso' del paquete SSIS invocaba como script externo. El
propio archivo Excel es producido, en un flujo previo, por el bot de
extracción de Power BI (203_bot_notas_de_credito).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from app.domain.exceptions import ExtraccionError
from app.domain.models import ColumnasNC

logger = logging.getLogger("etl_nc")

# El export de Power BI agrega 3 filas de pie de página (totales/filtros) que
# no son datos y se descartan antes de tipar.
FILAS_PIE_A_DESCARTAR = 3

_TIPOS_POR_COLUMNA: dict[str, pl.DataType] = {
    "RUT": pl.String,
    "RAZON_SOCIAL": pl.String,
    "FOLIO_NC": pl.String,
    "FECHA_NC": pl.Date,
    "NETO_NC": pl.Float64,
    "IVA_NC": pl.Float64,
    "TOTAL_NC": pl.Float64,
    "EJECUTIVO": pl.String,
}


class ExcelNotasCreditoExtractor:
    """Implementa el puerto ExtractorNotasCredito (app/application/ports.py)."""

    def __init__(self, excel_path: Path, columnas: ColumnasNC) -> None:
        self._excel_path = excel_path
        self._columnas = columnas

    def extraer(self) -> pl.DataFrame:
        df = self._leer_y_recortar()
        df = self._tipar(df)
        return df.select(list(self._columnas.nombres))

    def _leer_y_recortar(self) -> pl.DataFrame:
        try:
            df = pl.read_excel(self._excel_path)
        except Exception as exc:
            raise ExtraccionError(f"No se pudo leer el Excel '{self._excel_path}': {exc}") from exc

        logger.info("Archivo leído: %s filas", len(df))

        if len(df) < FILAS_PIE_A_DESCARTAR:
            logger.warning("El archivo tiene menos de %s filas; no se recorta el pie.", FILAS_PIE_A_DESCARTAR)
            return df

        df = df.slice(0, len(df) - FILAS_PIE_A_DESCARTAR)
        logger.info("Después de descartar el pie de página: %s filas", len(df))
        return df

    def _tipar(self, df: pl.DataFrame) -> pl.DataFrame:
        try:
            return df.with_columns(
                [pl.col(col).cast(dtype) for col, dtype in _TIPOS_POR_COLUMNA.items()]
            )
        except Exception as exc:
            raise ExtraccionError(f"No se pudieron convertir los tipos de datos: {exc}") from exc
