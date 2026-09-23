"""Excepciones del proceso de correos: copia SharePoint 'BPO' -> SharePoint
'ReportingFractalia', y consolidacion + carga a SQL Server ('CL_MOVIL').
No dependen de 'requests'/'pyodbc' ni de ninguna otra libreria externa."""

from __future__ import annotations


class CorreosError(Exception):
    """Error base de todo el proceso."""


class ConfiguracionError(CorreosError):
    """Falta una variable de entorno obligatoria (ver .env.example)."""


class PeriodoError(CorreosError):
    """FECHA_INICIO/FECHA_FIN (o --fecha-inicio/--fecha-fin) faltan, no se
    pueden interpretar como fecha, o el fin no es posterior al inicio."""


class SharePointResolutionError(CorreosError):
    """No se pudo resolver el site/drive/carpeta/archivo, o descargar el
    archivo, en SharePoint via Microsoft Graph."""


class SharePointUploadError(CorreosError):
    """Fallo subiendo un archivo a SharePoint via Microsoft Graph."""


class CargaError(CorreosError):
    """Fallo una operacion de lectura/escritura sobre SQL Server (CL_MOVIL)."""
