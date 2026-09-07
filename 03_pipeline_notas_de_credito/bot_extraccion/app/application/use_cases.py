"""
Caso de uso: orquesta Extract -> Load usando únicamente los puertos
definidos en application/ports.py. No conoce Playwright, dotenv ni el
sistema de archivos concreto -- eso es responsabilidad de infrastructure/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.ports import ArchivoLoader, ReportExtractor
from app.domain.models import ExportResult


@dataclass
class ExportarDetalleNCUseCase:
    """Extrae la tabla 'Detalle NC' de Power BI y la deposita en su destino final."""

    extractor: ReportExtractor
    loader: ArchivoLoader
    destino_final: Path

    def ejecutar(self) -> ExportResult:
        archivo_extraido = self.extractor.extraer()
        ruta_final = self.loader.guardar(archivo_extraido, self.destino_final)
        return ExportResult(ruta_archivo=ruta_final)
