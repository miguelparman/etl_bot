"""Lectura de archivos planos, equivalente a los Flat File Source de SSIS.

Cada Connection Manager de archivo plano del .dtsx original fijaba su propio
encoding/delimitador/calificador de texto por archivo; se replican tal cual
aqui en vez de asumir un formato unico para todos los CSV.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl


def read_aux_contacto(path: Path) -> pl.DataFrame:
    """Reporte_isn_aux_contacto_v2.csv

    Connection Manager original: delimitador ',', calificador de texto '"',
    CodePage=1252, 2 columnas: 'Número del caso', 'Id  de contacto'.
    """
    return pl.read_csv(
        path,
        separator=",",
        quote_char='"',
        encoding="cp1252",
        infer_schema_length=0,  # todas las columnas como Utf8 (igual que DT_WSTR de origen)
        null_values=[""],
    )


def read_aux_cliente(path: Path) -> pl.DataFrame:
    """Reporte_isn_aux_cliente_v2.csv

    Connection Manager original: delimitador ',', calificador de texto '"',
    CodePage=1252, columnas: 'Número del caso', 'Id  del cliente', 'Subsector',
    'Rango de trabajadores', 'Categoria Heredada', 'Descripción del negocio'.
    """
    return pl.read_csv(
        path,
        separator=",",
        quote_char='"',
        encoding="cp1252",
        infer_schema_length=0,
        null_values=[""],
    )
