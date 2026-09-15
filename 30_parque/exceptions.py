"""Excepciones del proceso de Parque. No dependen de pyodbc, pandas, requests
ni ninguna otra libreria externa."""

from __future__ import annotations


class ParqueError(Exception):
    """Error base de todo el proceso de carga de Parque."""


class ExtraccionError(ParqueError):
    """Fallo la descarga o el parseo del CSV de origen (SharePoint/Graph)."""


class ValidacionError(ParqueError):
    """Equivalente a errorRowDisposition/truncationRowDisposition='FailComponent'
    del Origen/Destino OLE DB original: detiene el flujo por un problema de
    columnas o de formato en los datos de origen."""


class CargaError(ParqueError):
    """Fallo una operacion de lectura/escritura sobre SQL Server (CL_PLANTA)."""


class PipelineError(ParqueError):
    """Envuelve cualquier excepcion no controlada ocurrida durante un paso del
    pipeline, identificando la rama (FIJO/MOVIL) y el paso donde ocurrio."""

    def __init__(self, pipeline: str, paso: str, causa: Exception) -> None:
        super().__init__(f"[{pipeline}] Fallo en '{paso}': {causa}")
        self.pipeline = pipeline
        self.paso = paso
        self.causa = causa
