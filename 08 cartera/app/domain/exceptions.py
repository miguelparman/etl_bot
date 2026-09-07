"""Excepciones de dominio. No dependen de pyodbc, pandas ni ninguna otra
libreria externa."""

from __future__ import annotations


class CarteraError(Exception):
    """Error base de todo el proceso de carga de Cartera."""


class ExtraccionError(CarteraError):
    """Fallo la lectura o el saneo del archivo Excel de origen (CARTERA_FRACTALIA.xlsx)."""


class ValidacionError(CarteraError):
    """Equivalente a un RAISERROR de la tarea 'VALIDA' del paquete original:
    detiene el pipeline por un problema de calidad de datos en la cartera
    temporal."""


class CargaError(CarteraError):
    """Fallo una operacion de lectura/escritura sobre SQL Server (staging,
    actual o historico)."""


class PipelineError(CarteraError):
    """Envuelve cualquier excepcion no controlada ocurrida durante un paso del
    pipeline, identificando el pipeline y el paso (Sequence Container /
    tarea) donde ocurrio."""

    def __init__(self, pipeline: str, paso: str, causa: Exception) -> None:
        super().__init__(f"[{pipeline}] Fallo en '{paso}': {causa}")
        self.pipeline = pipeline
        self.paso = paso
        self.causa = causa
