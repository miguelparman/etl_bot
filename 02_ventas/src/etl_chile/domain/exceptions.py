"""Excepciones de dominio. No dependen de ninguna capa externa."""


class EtlChileError(Exception):
    """Excepcion base para todos los errores del dominio del proyecto."""


class ConfigurationError(EtlChileError):
    """La configuracion de la aplicacion (env vars) es invalida o incompleta."""


class PipelineError(EtlChileError):
    """Un pipeline (equivalente a un paquete SSIS) fallo durante su ejecucion."""

    def __init__(self, pipeline_name: str, step: str, original_error: Exception):
        self.pipeline_name = pipeline_name
        self.step = step
        self.original_error = original_error
        super().__init__(
            f"Pipeline '{pipeline_name}' fallo en el paso '{step}': {original_error}"
        )
