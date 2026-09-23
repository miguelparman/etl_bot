"""Capa de infraestructura: ciclo de vida del navegador Playwright."""

from contextlib import contextmanager

from playwright.sync_api import Page, sync_playwright


@contextmanager
def crear_pagina(headless: bool) -> Page:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            yield page
        finally:
            browser.close()
