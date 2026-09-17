"""Extraccion: Origen OLE DB 'PQE_FIJO' / 'PQE_MO' de SSIS_Chile_parque.dtsx.

En el .dtsx original la extraccion era una consulta SQL parametrizada
('WHERE periodo = ?') contra Externos_Frac.dbo.pqe_fijtot2023 /
pqe_movtot2023. El origen cambio a un CSV publicado en SharePoint (ver
sharepoint/reader.py); como el CSV puede traer varios periodos mezclados, el
filtro que antes hacia SQL Server ahora lo hace validacion.py sobre el
DataFrame leido aqui -- extraer() solo descarga, no filtra ni valida.
"""

from __future__ import annotations

import logging

import pandas as pd

from models import ParqueFlowSpec
from sharepoint.reader import SharePointCsvReader

logger = logging.getLogger("parque")


def extraer(reader: SharePointCsvReader, spec: ParqueFlowSpec) -> pd.DataFrame:
    """Descarga y devuelve el CSV de origen del flujo, sin filtrar ni validar
    (eso es responsabilidad de validacion.py)."""
    df = reader.leer_csv(spec.archivo_csv)
    logger.info("[%s] CSV '%s' leido: %s filas", spec.nombre, spec.archivo_csv, len(df))
    return df
