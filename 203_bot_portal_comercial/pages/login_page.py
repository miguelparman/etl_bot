"""Page Object de la pantalla de login del Portal Comercial."""

from .base_page import BasePage


class LoginPage(BasePage):
    def ir_a_login(self, url: str) -> None:
        self.page.goto(url, wait_until="networkidle")

    def iniciar_sesion(self, usuario: str, password: str) -> None:
        self.page.locator("input[type='text']").first.fill(usuario)
        self.page.locator("input[type='password']").first.fill(password)

        boton_login = self.page.locator("button[type='submit'], input[type='submit']").first
        if boton_login.count() > 0:
            boton_login.click()
        else:
            self.page.locator("input[type='password']").first.press("Enter")

        self.page.wait_for_url("**/menu-principal.php", timeout=20000)
        self.page.wait_for_load_state("networkidle")
