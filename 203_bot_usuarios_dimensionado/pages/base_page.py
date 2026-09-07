"""Page Object base: helpers comunes a todas las pantallas del portal."""

import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

log = logging.getLogger("bot_dimensionado")


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def screenshot_diagnostico(self, log_dir: Path, nombre: str) -> None:
        try:
            ruta = log_dir / f"error_{nombre}_{datetime.now():%Y%m%d_%H%M%S}.png"
            self.page.screenshot(path=str(ruta), full_page=True)
            log.error("Captura de diagnostico guardada en: %s", ruta)
        except Exception:
            log.exception("No se pudo guardar la captura de diagnostico")
