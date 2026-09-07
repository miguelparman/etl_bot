"""
Bot de descarga del archivo PVTA_PROYECCION_PPP_FRACTALIA_PERU.csv desde el
Portal Comercial (comercial.telefonicachile.cl).

Requisitos
----------
- pip install playwright python-dotenv
- playwright install chromium
- Completar 203_bot_usuarios_dimensionado/.env (ver .env.example) con
  PORTAL_URL, PORTAL_USUARIO y PORTAL_PASSWORD. No subir ese archivo a
  ningun repositorio ni chat.

Arquitectura: Page Object Model + capas (config / core / pages / services).
Este archivo es el composition root: arma settings, logger, navegador,
page objects y el servicio del caso de uso, y los ejecuta.
"""

import logging
import sys

from config.settings import cargar_settings
from core.browser_factory import crear_pagina
from core.logger import configurar_logger
from pages.file_explorer_page import FileExplorerPage
from pages.login_page import LoginPage
from services.descarga_dimensionamiento_service import DescargaDimensionamientoService


def main() -> None:
    settings = cargar_settings()
    log = configurar_logger(settings.log_dir)

    with crear_pagina(settings.headless) as page:
        login_page = LoginPage(page)
        explorer_page = FileExplorerPage(page)
        service = DescargaDimensionamientoService(settings, login_page, explorer_page, log)
        service.ejecutar()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("bot_dimensionado").error("Proceso finalizado con error: %s", e)
        sys.exit(1)
