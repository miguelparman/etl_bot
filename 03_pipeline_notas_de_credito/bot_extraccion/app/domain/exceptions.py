"""Excepciones de dominio. No dependen de Playwright ni de ninguna otra librería externa."""


class ExportacionError(Exception):
    """Error base de todo el proceso de exportación."""


class AutenticacionError(ExportacionError):
    """La sesión de Power BI no pudo confirmarse (login pendiente o informe sin cargar)."""


class VisualNoEncontradoError(ExportacionError):
    """No se pudo localizar la página o el visual/tabla objetivo dentro del informe."""


class DescargaError(ExportacionError):
    """Falló el flujo de exportación/descarga dentro de Power BI."""


class GuardadoError(ExportacionError):
    """No se pudo depositar el archivo extraído en su destino final."""
