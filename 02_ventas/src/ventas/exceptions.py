"""Excepciones del proceso de VENTAS/SEÑALIZACIONES. No dependen de pyodbc,
pandas, requests ni ninguna otra libreria externa."""

from __future__ import annotations


class VentasError(Exception):
    """Error base de todo el proceso (paquetes Señalizaciones y Ventas)."""


class ExtraccionError(VentasError):
    """Fallo la descarga o el parseo de un Origen: CSV/Excel publicado en
    SharePoint, leido via Microsoft Graph."""


class ValidacionError(VentasError):
    """Equivalente a errorRowDisposition/truncationRowDisposition='FailComponent'
    del Origen/Destino OLE DB original: detiene el flujo por un problema de
    columnas o de formato en los datos de origen."""


class CargaError(VentasError):
    """Fallo una operacion de lectura/escritura sobre SQL Server (CL_USUARIOS
    o CL_DATA)."""


class PipelineError(VentasError):
    """Envuelve cualquier excepcion no controlada ocurrida durante un paso del
    pipeline, identificando el sub-pipeline (paquete .dtsx original: 'senalizaciones'
    o 'ventas') y el paso (Sequence Container / tarea) donde ocurrio."""

    def __init__(self, pipeline: str, paso: str, causa: Exception) -> None:
        super().__init__(f"[{pipeline}] Fallo en '{paso}': {causa}")
        self.pipeline = pipeline
        self.paso = paso
        self.causa = causa
