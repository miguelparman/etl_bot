"""Replica exacta del componente "Conversion de datos" del Data Flow
"TBL_ISN_ENVIOS_CONSOLIDADOS" (Package\\TBL_ISN_CALIDAD\\ACTUALIZACION SERVIDOR).

En el .dtsx original, TODAS las columnas tenian
errorRowDisposition="FailComponent" y truncationRowDisposition="FailComponent":
cualquier error de conversion o de truncado abortaba la tarea, no la
"arreglaba" silenciosamente. Este modulo preserva ese comportamiento: lanza
ValueError ante datos que el pipeline original habria hecho fallar.
"""
from __future__ import annotations

import polars as pl

SUBSEGMENTO_MAX_LEN = 20  # DT_WSTR(20) en el destino; el origen permite 30


class ConversionError(ValueError):
    """Equivalente a un fallo de componente por conversion/truncado (FailComponent)."""


def apply_envios_consolidado_casts(df: pl.DataFrame) -> pl.DataFrame:
    """Aplica los mismos casts que el componente Data Convert original:

    - FECHA_EVENTO: string -> Int32 (falla si no es num rico convertible)
    - Numero del caso: string -> Int32 (falla si no es convertible)
    - SUBSEGMENTO: falla si excede 20 caracteres (el original trunca con
      FailComponent, es decir, en la practica ABORTA en vez de truncar)
    """
    out = df

    for col in ("FECHA_EVENTO", "Número del caso"):
        try:
            out = out.with_columns(pl.col(col).cast(pl.Int32, strict=True))
        except pl.exceptions.InvalidOperationError as exc:
            raise ConversionError(
                f"No se pudo convertir la columna '{col}' a entero "
                f"(equivalente a fallo de 'Conversión de datos' en SSIS): {exc}"
            ) from exc

    subsegmento_lengths = out.select(
        pl.col("SUBSEGMENTO").str.len_chars().alias("len")
    )["len"]
    too_long = subsegmento_lengths.filter(subsegmento_lengths > SUBSEGMENTO_MAX_LEN)
    if too_long.len() > 0:
        raise ConversionError(
            f"{too_long.len()} fila(s) con SUBSEGMENTO de mas de "
            f"{SUBSEGMENTO_MAX_LEN} caracteres: el Data Flow original fallaba "
            f"el componente en este caso (truncationRowDisposition=FailComponent), "
            f"no truncaba silenciosamente."
        )

    return out
