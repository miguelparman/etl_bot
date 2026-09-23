"""Capa de aplicacion: caso de uso 'descargar REPORTE_AGENTES_FRACTALIA_SEM.csv
y subirlo a SharePoint'.

El archivo esta en la raiz de CALLCENTER > Fractalia (sin subcarpetas). Se
sube via Microsoft Graph a cada destino de settings.destinos_sharepoint.
Supone que la sesion del portal ya esta iniciada.
"""

import logging
from pathlib import Path

from config.settings import Settings
from pages.file_explorer_page import FileExplorerPage
from services.entrega_sharepoint import subir_a_sharepoint


class DescargaReporteAgentesService:
    def __init__(self, settings: Settings, explorer_page: FileExplorerPage, log: logging.Logger):
        self.settings = settings
        self.explorer_page = explorer_page
        self.log = log

    def ejecutar(self) -> None:
        s = self.settings

        try:
            self.log.info("Navegando CALLCENTER > Fractalia...")
            self.explorer_page.abrir_modulo_fractalia(s.carpeta_fractalia)

            self.log.info("Descargando %s...", s.archivo_reporte_agentes)
            download = self.explorer_page.descargar_archivo(s.archivo_reporte_agentes)
            contenido = Path(download.path()).read_bytes()
            if not contenido:
                raise RuntimeError("El archivo descargado quedo vacio (0 bytes)")
            self.log.info("Descarga OK (%s bytes)", len(contenido))

        except Exception:
            self.log.exception("Error durante la descarga de %s", s.archivo_reporte_agentes)
            self.explorer_page.screenshot_diagnostico(s.log_dir, "reporte_agentes")
            raise

        subir_a_sharepoint(s.destinos_sharepoint, s.archivo_reporte_agentes, contenido, s.graph_timeout_ms, self.log)
