"""Validación de los dos CSV auxiliares antes de cargarlos."""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def validar_no_vacio(df: pd.DataFrame, nombre: str, columnas_esperadas: list[str]) -> None:
    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas esperadas en '{nombre}': {faltantes}")
    if df.empty:
        logger.warning("'%s' no trae filas -- se carga vacío, igual que haría SSIS.", nombre)
