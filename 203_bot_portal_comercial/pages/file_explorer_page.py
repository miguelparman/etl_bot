"""Page Object del explorador de carpetas/reportes del Portal Comercial
(plugin jQuery File Tree bajo CALLCENTER)."""

from playwright.sync_api import Download

from .base_page import BasePage


class FileExplorerPage(BasePage):
    def abrir_modulo_fractalia(self, selector: str) -> None:
        # El modulo esta oculto tras un dropdown hover-only; se dispara el
        # handler de click directamente sobre el elemento del DOM.
        self.page.eval_on_selector(selector, "el => el.click()")
        self.page.wait_for_timeout(2500)

    def abrir_carpeta(self, ruta_rel: str) -> None:
        loc = self.page.locator(f'a[rel="{ruta_rel}"]')
        loc.wait_for(state="visible", timeout=15000)
        loc.click()
        self.page.wait_for_timeout(2000)

    def descargar_archivo(self, nombre_archivo: str) -> Download:
        boton_archivo = self.page.get_by_role("button", name=nombre_archivo).first
        if boton_archivo.count() == 0:
            boton_archivo = self.page.locator(f"button:has-text('{nombre_archivo}')").first
        if boton_archivo.count() == 0:
            raise RuntimeError(f"No se encontro el archivo '{nombre_archivo}' en la carpeta actual")

        with self.page.expect_download(timeout=60000) as download_info:
            boton_archivo.click()
        return download_info.value
