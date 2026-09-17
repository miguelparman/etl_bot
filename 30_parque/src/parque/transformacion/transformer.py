"""Transformacion: el .dtsx original no tiene componentes de negocio en estos
2 Data Flows (sin Derived Column, Data Conversion, Lookup, Conditional
Split, Merge, Aggregate, Sort -- ver README, seccion 'Notas de fidelidad').
El unico paso real es reordenar las columnas al orden exacto que espera el
Destino OLE DB de cada tabla, igual que hacia el mapeo 1:1 por nombre del
componente original.
"""

from __future__ import annotations

import pandas as pd

from models import ParqueFlowSpec


def reordenar_columnas(df: pd.DataFrame, spec: ParqueFlowSpec) -> pd.DataFrame:
    return df[list(spec.nombres_columnas)]
