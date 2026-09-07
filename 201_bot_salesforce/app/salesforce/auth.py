"""
Flujo de autenticacion interactiva de Salesforce (login + MFA).

IMPORTANTE: este modulo NUNCA intenta automatizar, saltarse o interceptar
la verificacion MFA (push de Salesforce Authenticator o PIN de 6 digitos).
Su unica responsabilidad es: (1) rellenar usuario/contrasena si el
formulario esta presente, (2) detectar si Salesforce ya nos dejo pasar a
la app Lightning, y (3) esperar pasivamente (polling) a que el propio
usuario complete la aprobacion en su telefono o el PIN dentro de la pagina.
"""

from __future__ import annotations

import time

from playwright.sync_api import BrowserContext, Page

from app.logger import log

# Los ids "#username" / "#password" / "#Login" pertenecen a la pagina de
# login estandar de Salesforce (login.salesforce.com y dominios My Domain
# como telefonicab2b.my.salesforce.com), no a un componente Lightning con
# ids dinamicos por sesion. Son estables entre ejecuciones y estan
# documentados por Salesforce, por eso se usan aqui en vez de get_by_label
# (la pagina de login no siempre expone labels accesibles consistentes
# entre idiomas de la org).
_USERNAME_SELECTOR = "#username"
_PASSWORD_SELECTOR = "#password"
_LOGIN_BUTTON_SELECTOR = "#Login"

_MFA_BANNER = """
==================================================
SE REQUIERE AUTENTICACION MULTIFACTOR
==================================================

Por favor:

1. Completa el login de Salesforce.
2. Aprueba la solicitud en Salesforce Authenticator.
3. Si se solicita un codigo de 6 digitos,
   introducelo manualmente en Salesforce.

Esperando autenticacion...
==================================================
"""

_PROGRESS_INTERVAL_S = 30


def is_authenticated(context: BrowserContext) -> bool:
    """Solo se considera autenticado si ALGUNA pestana del contexto aterrizo
    en la app Lightning real (URL con '/lightning/') Y existe la cookie de
    sesion 'sid'. Salesforce fija esa cookie de forma temprana durante el
    propio paso de verificacion MFA (para poder mostrar la pantalla de
    verificacion), antes de que el usuario la confirme; por eso la cookie
    sola no basta como senal de login completado.

    Se revisan TODAS las pestanas del contexto (no solo la que abrimos
    originalmente) porque algunos flujos de login/MFA de Salesforce
    redirigen o completan la verificacion en una pestana/ventana nueva; las
    cookies pertenecen al contexto entero, asi que cualquier pestana sirve
    como senal.
    """
    if not any(c.get("name") == "sid" for c in context.cookies()):
        return False
    for page in context.pages:
        try:
            if "/lightning/" in page.url:
                return True
        except Exception:
            continue
    return False


def _diagnostic_snapshot(context: BrowserContext) -> str:
    try:
        urls = [p.url for p in context.pages]
        cookie_names = sorted({c.get("name", "") for c in context.cookies()})
    except Exception as exc:
        return f"(no se pudo inspeccionar el contexto: {exc})"
    return f"paginas abiertas: {urls} | cookies presentes: {cookie_names}"


def fill_login_form(page: Page, username: str, password: str) -> None:
    """Rellena usuario y contrasena si el formulario de login esta
    presente. Si Salesforce ya paso la pantalla de credenciales (p.ej. una
    sesion parcial que solo pide MFA), no hace nada.
    """
    username_field = page.locator(_USERNAME_SELECTOR)
    try:
        username_field.wait_for(state="visible", timeout=5_000)
    except Exception:
        log.info(
            "No se encontro el formulario de usuario/contrasena "
            "(es posible que Salesforce ya este esperando solo el MFA)."
        )
        return

    username_field.fill(username)
    page.locator(_PASSWORD_SELECTOR).fill(password)
    page.locator(_LOGIN_BUTTON_SELECTOR).click()
    log.info("Formulario de usuario/contrasena enviado.")


def wait_for_interactive_login(context: BrowserContext, timeout_ms: int) -> bool:
    """Muestra el aviso de MFA y espera, sin intervenir, a que el login
    finalice, sondeando el estado del contexto hasta `timeout_ms`.

    Devuelve True si se detecto login exitoso dentro del tiempo de espera.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    banner_shown = False
    last_progress = time.monotonic()

    while time.monotonic() < deadline:
        if is_authenticated(context):
            log.info("Autenticacion de Salesforce completada.")
            return True
        if not banner_shown:
            # Se usa el logger (no print()) para que tambien quede en el
            # archivo de log y no falle si se ejecuta con pythonw.exe (sin
            # consola, sys.stdout es None) -- aunque este flujo interactivo
            # no deberia alcanzarse en una tarea programada desatendida.
            log.warning(_MFA_BANNER)
            banner_shown = True
        if time.monotonic() - last_progress >= _PROGRESS_INTERVAL_S:
            remaining = int(deadline - time.monotonic())
            # Diagnostico (sin datos sensibles: solo URLs y nombres de
            # cookies, nunca valores) para poder ver de inmediato por que
            # no se detecta el login si algo no coincide con lo esperado.
            log.info(
                "Esperando autenticacion manual... (%ss restantes) | %s",
                remaining,
                _diagnostic_snapshot(context),
            )
            last_progress = time.monotonic()
        time.sleep(1)

    return False
