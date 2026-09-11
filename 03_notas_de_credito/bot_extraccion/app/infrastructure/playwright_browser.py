"""Adaptador de infraestructura: ciclo de vida del navegador Playwright."""

from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import BrowserContext, Page, Playwright

from app.domain.models import ExportSettings
from app.infrastructure.logging_setup import NOMBRE_LOGGER

logger = logging.getLogger(NOMBRE_LOGGER)


class NavegadorPowerBI:
    """
    Encapsula el contexto persistente de Chromium: la sesión de
    Microsoft/Power BI queda guardada en 'profile_dir', por lo que no hace
    falta guardar usuario/contraseña en el código.
    """

    def __init__(self, settings: ExportSettings, playwright: Playwright) -> None:
        self._settings = settings
        self._playwright = playwright
        self.context: Optional[BrowserContext] = None

    def iniciar(self) -> BrowserContext:
        logger.info("Abriendo Power BI...")
        self._settings.profile_dir.mkdir(parents=True, exist_ok=True)
        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._settings.profile_dir),
            headless=self._settings.headless,
            slow_mo=self._settings.slow_mo,
            accept_downloads=True,
            viewport={"width": 1600, "height": 900},
        )
        self.context.set_default_timeout(self._settings.nav_timeout)
        return self.context

    def nueva_pagina(self) -> Page:
        """
        Abre (o reutiliza) una pestaña. Se expone por separado de la
        navegación al informe para que el llamador conserve la referencia a
        'page' incluso si la navegación posterior falla (necesario para
        poder tomar captura de pantalla del error).
        """
        assert self.context is not None, "Llama a iniciar() antes de nueva_pagina()."
        page = self.context.pages[0] if self.context.pages else self.context.new_page()
        page.bring_to_front()
        return page

    def cerrar(self) -> None:
        if self.context is not None:
            self.context.close()
            self.context = None
