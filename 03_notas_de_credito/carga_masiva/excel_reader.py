"""Lectura y depuración del Excel de origen (NC_.xlsx).

El export de Power BI agrega, al final del archivo, filas de pie de página
que no son datos: una fila 'Total', una fila en blanco separadora y una fila
'Filtros aplicados: ...'. OJO: no se puede asumir una cantidad fija de filas
de pie -- se confirmó en vivo que 'pl.read_excel' descarta silenciosamente la
fila en blanco (no la cuenta como fila de la hoja), así que el pie a veces
mide 3 filas y a veces 2. Por eso el pie se detecta por CONTENIDO, mirando
solo la cola del archivo (nunca todo el archivo, para no arriesgarse a
recortar filas de datos reales que por algún motivo tengan RUT vacío en
medio del dataset). Este mismo criterio corrigió un bug real en
'etl_carga' donde un archivo con 187 filas de datos cargaba solo 186 por
asumir un pie de tamaño fijo.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from config import COLUMNAS

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


def leer_excel(excel_path: Path) -> pl.DataFrame:
    df = pl.read_excel(excel_path)
    df = _descartar_pie_de_pagina(df)
    df = df.with_columns([pl.col(col).cast(dtype) for col, dtype in _TIPOS_POR_COLUMNA.items()])
    return df.select(list(COLUMNAS))


def _descartar_pie_de_pagina(df: pl.DataFrame) -> pl.DataFrame:
    """Cuenta cuántas filas AL FINAL son de pie de página (fila totalmente
    vacía, RUT = 'Total', o RUT que empieza con 'Filtros aplicad'), mirando
    solo desde la última fila hacia atrás y deteniéndose en la primera fila
    que no lo sea."""
    total = len(df)
    limite = min(total, 10)  # el pie de Power BI son a lo sumo un par de filas
    if limite == 0:
        return df

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

    return df.slice(0, total - recorte) if recorte > 0 else df
