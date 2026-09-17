"""
SalesforceClient: ciclo de vida de Playwright (browser/context/sesion) y
navegacion autenticada a Salesforce.

Un unico Browser + BrowserContext se crea por ejecucion y se reutiliza para
todos los reportes (ver Fase 1, punto 25): nunca se abre un navegador nuevo
por informe.
"""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from app.logger import log
from app.salesforce import auth

# Comprobacion rapida (sin mostrar el aviso de MFA) de si una sesion
# reutilizada via storage_state sigue siendo valida.
_SESSION_REUSE_TIMEOUT_MS = 15_000
_SESSION_REUSE_POLL_S = 0.5


class SalesforceClient:
    def __init__(
        self,
        domain: str,
        username: str,
        password: str,
        auth_state_path: Path,
        manual_login_timeout_minutes: int,
        page_timeout_ms: int,
        headless: bool,
    ) -> None:
        self._domain = domain
        self._username = username
        self._password = password
        self._auth_state_path = auth_state_path
        self._manual_login_timeout_ms = manual_login_timeout_minutes * 60_000
        self._page_timeout_ms = page_timeout_ms
        self._headless = headless

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def __enter__(self) -> "SalesforceClient":
        self._playwright = sync_playwright().start()
        self.ensure_authenticated()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def new_page(self) -> Page:
        if self._context is None:
            raise RuntimeError("La sesion de Salesforce no esta lista (llama a ensure_authenticated primero).")
        page = self._context.new_page()
        page.set_default_timeout(self._page_timeout_ms)
        return page

    def ensure_authenticated(self) -> None:
        if self._auth_state_path.exists():
            log.info("Sesion de Salesforce previa encontrada, comprobando validez...")
            if self._try_reuse_session():
                return
            log.warning("La sesion guardada ya no es valida.")
        else:
            log.info("No existe una sesion de Salesforce guardada.")

        self._interactive_login()

        # El login interactivo siempre usa un navegador visible (el MFA lo
        # exige), pero una vez guardada la sesion se reabre respetando
        # HEADLESS: con HEADLESS=true el resto del procesamiento corre sin
        # ventana (la visible solo aparecio para el login/MFA); con
        # HEADLESS=false se mantiene visible. _try_reuse_session ya
        # implementa exactamente esa apertura + verificacion.
        if not self._try_reuse_session():
            raise RuntimeError(
                "La sesion de Salesforce recien guardada no se pudo validar al reabrirla. "
                f"Revisa el archivo de sesion: {self._auth_state_path}"
            )

    def _try_reuse_session(self) -> bool:
        browser = self._playwright.chromium.launch(headless=self._headless)
        context = browser.new_context(storage_state=str(self._auth_state_path))
        page = context.new_page()
        page.set_default_timeout(self._page_timeout_ms)
        try:
            page.goto(self._domain, wait_until="domcontentloaded")
            if self._poll_authenticated(context, timeout_ms=_SESSION_REUSE_TIMEOUT_MS):
                log.info("Sesion de Salesforce valida, se reutiliza (headless=%s).", self._headless)
                page.close()
                self._browser = browser
                self._context = context
                return True
        finally:
            if self._context is not context:
                context.close()
                browser.close()
        return False

    def _interactive_login(self) -> None:
        """Realiza el login/MFA en un navegador visible y guarda la sesion.

        Este navegador se cierra siempre al terminar (con exito o error):
        no queda como el contexto activo del cliente. Quien continua el
        procesamiento es ensure_authenticated(), reabriendo la sesion recien
        guardada respetando HEADLESS.
        """
        log.info("Iniciando login interactivo de Salesforce (navegador visible)...")
        # --start-maximized + no_viewport: bajo el Programador de tareas la
        # ventana puede abrirse detras de otras o con un tamaño reducido y
        # pasar desapercibida; maximizarla y traerla al frente la hace mucho
        # mas dificil de perder de vista.
        browser = self._playwright.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.set_default_timeout(self._page_timeout_ms)

        try:
            page.bring_to_front()
            page.goto(self._domain, wait_until="domcontentloaded")
            auth.fill_login_form(page, self._username, self._password)

            if not auth.wait_for_interactive_login(context, timeout_ms=self._manual_login_timeout_ms):
                raise RuntimeError(
                    "No se detecto el inicio de sesion en Salesforce dentro del tiempo de espera "
                    f"({self._manual_login_timeout_ms // 60_000} minutos)."
                )

            self._auth_state_path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(self._auth_state_path))
            log.info("Sesion de Salesforce guardada en %s", self._auth_state_path)
        except Exception:
            # Sin esto, una excepcion aqui (p.ej. un fallo al lanzar
            # Chromium o al navegar) se pierde en completo silencio bajo
            # pythonw.exe (sys.stderr es None: no hay traceback en ninguna
            # parte). Se deja constancia explicita en el log del dia.
            log.exception("Fallo el login interactivo de Salesforce.")
            raise
        finally:
            context.close()
            browser.close()

    def _poll_authenticated(self, context: BrowserContext, timeout_ms: int) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if auth.is_authenticated(context):
                return True
            time.sleep(_SESSION_REUSE_POLL_S)
        return False
