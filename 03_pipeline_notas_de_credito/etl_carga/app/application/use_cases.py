"""Caso de uso: orquesta el pipeline completo usando únicamente los puertos
definidos en application/ports.py. No conoce pyodbc, polars ni el archivo
Excel concreto -- eso es responsabilidad de infrastructure/.

El orden de pasos reproduce exactamente las PrecedenceConstraints del paquete
SSIS_CL_NC.dtsx dentro de 'Contenedor de secuencias':

    Tarea Ejecutar proceso (ETL_NC_polars.py) -> DELETE -> DELETE 2
        -> DELETE NC -> CARGA NC -> UPDATE
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports import DestinoRepository, ExtractorNotasCredito, StagingRepository
from app.domain.models import PeriodoCarga, ResultadoETL


@dataclass
class CargarNotasDeCreditoUseCase:
    """Recarga las Notas de Crédito de un período: Excel -> staging -> destino."""

    extractor: ExtractorNotasCredito
    staging: StagingRepository
    destino: DestinoRepository
    periodo: PeriodoCarga

    def ejecutar(self) -> ResultadoETL:
        # Tarea Ejecutar proceso: extrae del Excel y puebla TBL_NC_Temp desde cero.
        df_extraido = self.extractor.extraer()
        self.staging.truncar()
        self.staging.insertar(df_extraido)

        # DELETE + DELETE 2: depura staging antes de tocar la tabla final.
        self.staging.eliminar_fuera_de_periodo(self.periodo)
        self.staging.eliminar_filas_invalidas()

        # DELETE NC: limpia el período en destino para evitar duplicados.
        filas_eliminadas = self.destino.eliminar_periodo(self.periodo)

        # CARGA NC: copia staging depurado -> destino.
        df_staging = self.staging.leer_todo()
        filas_cargadas = self.destino.cargar_desde(df_staging)

        # UPDATE: homologación de nombres de ejecutivo para el período.
        filas_normalizadas = self.destino.normalizar_ejecutivos(self.periodo)

        return ResultadoETL(
            periodo=self.periodo,
            filas_extraidas=len(df_extraido),
            filas_staging_tras_limpieza=len(df_staging),
            filas_eliminadas_destino=filas_eliminadas,
            filas_cargadas_destino=filas_cargadas,
            filas_ejecutivo_normalizadas=filas_normalizadas,
        )
