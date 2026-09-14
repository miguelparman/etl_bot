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

# El export de Power BI agrega filas de pie de página al final (fila de
# "Total", una fila en blanco separadora y una fila "Filtros aplicados: ...")
# que no son datos. OJO: no se puede asumir una cantidad fija de filas de pie
# -- se confirmó en vivo que 'pl.read_excel' descarta silenciosamente la fila
# en blanco (no la cuenta como fila de la hoja), así que a veces el pie mide 3
# filas y a veces 2. Recortar un número fijo del final hacía que, cuando el
# pie medía 2, se comiera también la última fila real de datos (bug real:
# archivo con 187 filas de datos terminó cargando solo 186). Por eso el pie se
# detecta por CONTENIDO (ver '_indice_inicio_pie'), no por conteo.
_VALORES_RUT_PIE = ("Total", "Filtros aplicad")

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

        corte = self._indice_inicio_pie(df)
        if corte is None:
            logger.warning(
                "No se detectó el pie de página del export de Power BI "
                "(fila 'Total' / 'Filtros aplicados'); se usan todas las "
                "filas tal cual."
            )
            return df

        df = df.slice(0, corte)
        logger.info("Después de descartar el pie de página: %s filas", len(df))
        return df

    @staticmethod
    def _indice_inicio_pie(df: pl.DataFrame) -> int | None:
        """
        Cuenta cuántas filas AL FINAL del archivo son de pie de página (fila
        totalmente vacía, RUT = 'Total', o RUT que empieza con 'Filtros
        aplicad'), mirando solo desde la última fila hacia atrás y
        deteniéndose en la primera fila que no lo sea.

        OJO: se busca solo en la cola (no en todo el archivo) a propósito --
        si se buscara en todo el archivo, una fila real con RUT nulo en
        cualquier parte del dataset (no solo al final) recortaría de más y
        se perderían filas de datos válidas.
        """
        total = len(df)
        limite = min(total, 10)  # el pie de Power BI son a lo sumo un par de filas
        if limite == 0:
            return None

        recorte = 0
        for fila in reversed(df.tail(limite).rows(named=True)):
            rut = fila.get("RUT")
            vacia = all(valor is None for valor in fila.values())
            es_total_o_filtros = isinstance(rut, str) and (
                rut in _VALORES_RUT_PIE or rut.startswith(_VALORES_RUT_PIE[1])
            )
            if vacia or es_total_o_filtros:
                recorte += 1
            else:
                break

        return total - recorte if recorte > 0 else None

    def _tipar(self, df: pl.DataFrame) -> pl.DataFrame:
        try:
            return df.with_columns(
                [pl.col(col).cast(dtype) for col, dtype in _TIPOS_POR_COLUMNA.items()]
            )
        except Exception as exc:
            raise ExtraccionError(f"No se pudieron convertir los tipos de datos: {exc}") from exc
