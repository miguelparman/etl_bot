"""
Adaptador de infraestructura: utilidades de diagnóstico y captura de
errores. No forman parte del flujo de negocio, pero son claves para poder
depurar cuando Power BI cambia su interfaz y algún selector deja de
funcionar.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

from app.infrastructure.logging_setup import NOMBRE_LOGGER

logger = logging.getLogger(NOMBRE_LOGGER)


def diagnosticar_pagina(page: Page) -> None:
    """Vuelca en el log las pestañas, títulos de visual y botones "..." detectados."""
    logger.info("=== DIAGNOSTICO DE PAGINA ===")
    try:
        pestanas = page.locator("[role='tab']")
        logger.info(f"Pestañas encontradas ({pestanas.count()}):")
        for i in range(min(pestanas.count(), 30)):
            try:
                logger.info(f"  - '{pestanas.nth(i).inner_text()}'")
            except Exception:
                pass

        titulos = page.locator("[class*='visualTitle'], [class*='visual-title']")
        logger.info(f"Títulos de visual encontrados ({titulos.count()}):")
        for i in range(min(titulos.count(), 50)):
            try:
                logger.info(f"  - '{titulos.nth(i).inner_text()}'")
            except Exception:
                pass

        botones_opciones = page.locator(
            "button[aria-label*='options' i], button[aria-label*='opciones' i]"
        )
        logger.info(f"Botones de opciones (...) encontrados: {botones_opciones.count()}")
    except Exception:
        logger.exception("Fallo al recolectar información de diagnóstico.")
    logger.info("=== FIN DIAGNOSTICO ===")


def tomar_captura_error(page: Optional[Page], screenshots_dir: Path, etiqueta: str) -> Optional[Path]:
    if page is None:
        return None
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    ruta = screenshots_dir / f"error_{etiqueta}_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        page.screenshot(path=str(ruta), full_page=True)
        logger.info(f"Captura de pantalla guardada en: {ruta}")
        return ruta
    except Exception:
        logger.exception("No se pudo tomar captura de pantalla del error.")
        return None
