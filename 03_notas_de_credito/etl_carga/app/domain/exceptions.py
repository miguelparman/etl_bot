"""Excepciones de dominio. No dependen de pyodbc, polars ni ninguna otra librería externa."""


class ETLError(Exception):
    """Error base de todo el proceso de carga de Notas de Crédito."""


class ExtraccionError(ETLError):
    """Falló la lectura o el saneo del archivo Excel de origen."""


class StagingError(ETLError):
    """Falló una operación sobre la tabla de staging (TBL_NC_Temp)."""


class CargaDestinoError(ETLError):
    """Falló una operación sobre la tabla destino (TBL_NC_DB)."""
