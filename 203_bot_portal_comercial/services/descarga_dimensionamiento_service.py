"""Capa de aplicacion: caso de uso 'descargar el archivo de dimensionamiento
y subirlo a SharePoint'.

El archivo esta en CALLCENTER > Fractalia > POST VENTA > DIMENSIONAMIENTO. Se
sube via Microsoft Graph a cada destino de settings.destinos_sharepoint (ya
no se guarda en disco local). Supone que la sesion del portal ya esta
iniciada. No conoce selectores ni detalles DOM.
"""

import logging
from pathlib import Path

from config.settings import Settings
from pages.file_explorer_page import FileExplorerPage
from services.entrega_sharepoint import subir_a_sharepoint


class DescargaDimensionamientoService:
    def __init__(self, settings: Settings, explorer_page: FileExplorerPage, log: logging.Logger):
        self.settings = settings
        self.explorer_page = explorer_page
        self.log = log

    def ejecutar(self) -> None:
        s = self.settings

        try:
            self.log.info("Navegando CALLCENTER > Fractalia > POST VENTA > DIMENSIONAMIENTO...")
            self.explorer_page.abrir_modulo_fractalia(s.carpeta_fractalia)
            self.explorer_page.abrir_carpeta(s.ruta_post_venta)
            self.explorer_page.abrir_carpeta(s.ruta_dimensionamiento)

            self.log.info("Descargando %s...", s.archivo_objetivo)
            download = self.explorer_page.descargar_archivo(s.archivo_objetivo)
            contenido = Path(download.path()).read_bytes()
            if not contenido:
                raise RuntimeError("El archivo descargado quedo vacio (0 bytes)")
            self.log.info("Descarga OK (%s bytes)", len(contenido))

        except Exception:
            self.log.exception("Error durante la descarga de %s", s.archivo_objetivo)
            self.explorer_page.screenshot_diagnostico(s.log_dir, "descarga")
            raise

        subir_a_sharepoint(s.destinos_sharepoint, s.archivo_objetivo, contenido, s.graph_timeout_ms, self.log)
