"""Capa de aplicacion: caso de uso 'descargar el archivo de dimensionamiento'.

Orquesta las page objects (login, exploracion de carpetas) para cumplir el
flujo completo y valida el resultado. No conoce selectores ni detalles DOM.
"""

import logging

from config.settings import Settings
from pages.file_explorer_page import FileExplorerPage
from pages.login_page import LoginPage


class DescargaDimensionamientoService:
    def __init__(
        self,
        settings: Settings,
        login_page: LoginPage,
        explorer_page: FileExplorerPage,
        log: logging.Logger,
    ):
        self.settings = settings
        self.login_page = login_page
        self.explorer_page = explorer_page
        self.log = log

    def ejecutar(self) -> None:
        s = self.settings

        if not s.destino.parent.exists():
            raise FileNotFoundError(f"No existe la carpeta destino: {s.destino.parent}")

        try:
            self.log.info("Accediendo al Portal Comercial...")
            self.login_page.ir_a_login(s.portal_url)
            self.login_page.iniciar_sesion(s.portal_usuario, s.portal_password)
            self.log.info("Login OK")

            self.log.info("Navegando CALLCENTER > Fractalia > POST VENTA > DIMENSIONAMIENTO...")
            self.explorer_page.abrir_modulo_fractalia(s.carpeta_fractalia)
            self.explorer_page.abrir_carpeta(s.ruta_post_venta)
            self.explorer_page.abrir_carpeta(s.ruta_dimensionamiento)

            self.log.info("Descargando %s...", s.archivo_objetivo)
            download = self.explorer_page.descargar_archivo(s.archivo_objetivo)
            download.save_as(str(s.destino))

            tamanio = s.destino.stat().st_size
            if tamanio == 0:
                raise RuntimeError("El archivo descargado quedo vacio (0 bytes)")

            self.log.info("Archivo guardado en %s (%s bytes)", s.destino, tamanio)

        except Exception:
            self.log.exception("Error durante la descarga")
            self.explorer_page.screenshot_diagnostico(s.log_dir, "descarga")
            raise
