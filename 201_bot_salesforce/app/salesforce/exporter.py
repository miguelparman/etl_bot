"""
SalesforceReportExporter: exportacion de un informe individual de
Salesforce Lightning a CSV (Solo detalles / Delimitado por comas /
ISO-8859-1), y validacion basica del archivo resultante.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import FrameLocator, Locator, Page

from app.logger import log

# El visor de informes de Salesforce Lightning se ejecuta dentro de un
# iframe propio (lightningReportApp.app?reportId=...), no en el documento
# principal de la pestana -- confirmado inspeccionando los frames reales de
# la pagina (Playwright no busca dentro de iframes salvo que se indique
# explicitamente el frame). Se localiza por un fragmento estable de la URL
# del iframe en vez de su "name" (que incluye un sufijo numerico que
# cambia entre cargas).
_REPORT_FRAME_SELECTOR = "iframe[src*='lightningReportApp.app']"

# El boton que despliega el menu "Modificar" (Guardar, Suscribir, Exportar,
# Eliminar, ...) no expone un aria-label propio, pero SI tiene un texto de
# asistencia oculto ("slds-assistive-text") que Playwright usa como su
# nombre accesible al resolver get_by_role.
_MORE_ACTIONS_BUTTON_NAME = "Más acciones - Modificar"
_EXPORT_MENU_ITEM_TEXT = "Exportar"

_DETAIL_ONLY_LABEL = "Solo detalles"
_FORMAT_LABEL = "Formato"
# Existen dos opciones de "Delimitado por comas":
#   - "Delimitado por comas .csv": usa el separador de la configuracion
#     regional del usuario, que para configuraciones en español suele ser
#     ";" en vez de ",".
#   - "Delimitado por comas (distinto a la configuracion regional) .csv":
#     fuerza la coma literal "," sin importar la configuracion regional.
# Se usa esta segunda para garantizar coma como separador real. Se usa solo
# el fragmento distintivo (no el texto completo, cuyo sufijo exacto no esta
# confirmado) para que el emparejamiento por substring en
# _select_option_by_text lo encuentre de forma inequivoca.
_FORMAT_OPTION_TEXT = "distinto a la configuración regional"
_ENCODING_LABEL = "Codificación"
_ENCODING_OPTION_TEXT = "ISO-8859-1"
_CONFIRM_EXPORT_BUTTON_TEXT = "Exportar"


class ReportExportError(Exception):
    """Fallo durante la exportacion o validacion de un informe."""


class SalesforceReportExporter:
    def __init__(
        self,
        page: Page,
        downloads_dir: Path,
        screenshots_dir: Path,
        download_timeout_ms: int,
    ) -> None:
        self._page = page
        self._downloads_dir = downloads_dir
        self._screenshots_dir = screenshots_dir
        self._download_timeout_ms = download_timeout_ms

    def export_report(self, url: str, filename: str) -> Path:
        """Ejecuta el flujo completo de exportacion y devuelve la ruta local del CSV."""
        try:
            log.info("Abriendo reporte: %s", url)
            self._page.goto(url, wait_until="domcontentloaded")

            self._open_export_menu()
            dialog = self._locate_export_dialog()
            self._configure_export_dialog(dialog)

            target_path = self._downloads_dir / filename
            # BrowserContext no tiene expect_download() (solo Page); se usa
            # expect_event a nivel de contexto para capturar la descarga
            # aunque el clic de confirmacion la dispare en una pestana
            # distinta a la que abrimos originalmente.
            with self._page.context.expect_event("download", timeout=self._download_timeout_ms) as download_info:
                self._confirm_export(dialog)
            download = download_info.value
            download.save_as(str(target_path))
            log.info("Archivo descargado: %s", target_path)

            self.validate_csv(target_path)
            log.info("CSV validado correctamente: %s", target_path)
            return target_path
        except Exception:
            self._save_error_screenshot(filename)
            raise

    def validate_csv(self, path: Path) -> None:
        """Lanza ReportExportError si el CSV no pasa las validaciones minimas."""
        if not path.exists():
            raise ReportExportError(f"El archivo no existe: {path}")
        if path.suffix.lower() != ".csv":
            raise ReportExportError(f"Extension inesperada (se esperaba .csv): {path}")
        if path.stat().st_size == 0:
            raise ReportExportError(f"El archivo esta vacio: {path}")
        try:
            with path.open(encoding="iso-8859-1") as fh:
                first_line = fh.readline()
        except OSError as exc:
            raise ReportExportError(f"No se pudo leer el archivo {path}: {exc}") from exc
        # Nota: ISO-8859-1 mapea cualquier byte a un caracter valido, por lo
        # que nunca lanza UnicodeDecodeError; esta lectura solo detecta
        # fallos de E/S (permisos, disco, archivo bloqueado), no corrupcion
        # de codificacion. Verificar la codificacion real requeriria un
        # analisis heuristico (chardet) fuera del alcance de esta fase.
        if not first_line.strip():
            raise ReportExportError(f"El archivo parece no tener contenido valido: {path}")

    # -- Pasos internos del flujo de exportacion ---------------------------

    def _report_frame(self) -> FrameLocator:
        return self._page.frame_locator(_REPORT_FRAME_SELECTOR)

    def _open_export_menu(self) -> None:
        frame = self._report_frame()
        frame.get_by_role("button", name=_MORE_ACTIONS_BUTTON_NAME).click()
        frame.get_by_text(_EXPORT_MENU_ITEM_TEXT, exact=True).click()

    def _locate_export_dialog(self) -> Locator:
        # El dialogo de exportacion se renderiza dentro del mismo iframe del
        # informe; se deja como respaldo la busqueda en el documento
        # principal por si algun tipo de informe no usa ese iframe.
        # Puede haber mas de un elemento con role=dialog en el DOM (p.ej.
        # modales ya cerrados pero no desmontados); .last toma el que se
        # acaba de abrir.
        dialog = self._report_frame().get_by_role("dialog").last
        try:
            dialog.wait_for(state="visible", timeout=5_000)
            return dialog
        except Exception:
            pass
        dialog = self._page.get_by_role("dialog").last
        dialog.wait_for(state="visible")
        return dialog

    def _configure_export_dialog(self, dialog: Locator) -> None:
        self._select_detail_only_view(dialog)
        self._select_option_by_text(dialog, _FORMAT_LABEL, _FORMAT_OPTION_TEXT)
        self._select_option_by_text(dialog, _ENCODING_LABEL, _ENCODING_OPTION_TEXT)

    def _select_detail_only_view(self, dialog: Locator) -> None:
        try:
            dialog.get_by_label(_DETAIL_ONLY_LABEL).check(timeout=3_000)
            return
        except Exception:
            pass
        # Fallback: en el "visual picker" de SLDS el input de radio puede
        # no tener una asociacion accesible con su texto; el propio texto
        # visible vive dentro del <label>, y un click ahi activa el radio
        # igual que en un navegador real (comportamiento nativo de <label>).
        dialog.get_by_text(_DETAIL_ONLY_LABEL, exact=True).click()

    def _select_option_by_text(self, dialog: Locator, label_text: str, option_text: str) -> None:
        select_el = self._locate_labeled_select(dialog, label_text)
        options = select_el.locator("option")
        texts = options.all_inner_texts()

        # Coincidencia exacta primero: algunos <select> de Salesforce tienen
        # opciones que comparten un mismo prefijo (p.ej. "Delimitado por
        # comas .csv" vs "Delimitado por comas (distinto a la configuración
        # regional) .csv"), asi que una busqueda por substring es ambigua.
        matches = [i for i, t in enumerate(texts) if t.strip() == option_text]
        if not matches:
            matches = [i for i, t in enumerate(texts) if option_text in t]

        if not matches:
            raise ReportExportError(
                f"No se encontro la opcion '{option_text}' dentro del selector '{label_text}'. "
                f"Opciones disponibles: {texts}"
            )
        if len(matches) > 1:
            raise ReportExportError(
                f"La opcion '{option_text}' es ambigua dentro de '{label_text}': "
                f"coincide con {[texts[i] for i in matches]}"
            )

        option_value = options.nth(matches[0]).get_attribute("value")
        select_el.select_option(value=option_value)

    def _locate_labeled_select(self, dialog: Locator, label_text: str) -> Locator:
        try:
            select_el = dialog.get_by_label(label_text)
            select_el.wait_for(state="visible", timeout=3_000)
            return select_el
        except Exception:
            pass
        # Fallback cuando el <select> no esta asociado via <label for=...>:
        # se ubica el contenedor de campo SLDS que contiene el texto de la
        # etiqueta y se toma el <select> dentro de ese mismo contenedor.
        return dialog.locator("div.slds-form-element", has_text=label_text).locator("select")

    def _confirm_export(self, dialog: Locator) -> None:
        dialog.get_by_role("button", name=_CONFIRM_EXPORT_BUTTON_TEXT, exact=True).click()

    def _save_error_screenshot(self, filename: str) -> None:
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem
        timestamp = f"{datetime.now():%Y%m%d_%H%M%S}"
        screenshot_path = self._screenshots_dir / f"{timestamp}_{stem}_error.png"
        try:
            self._page.screenshot(path=str(screenshot_path))
            log.error("Fallo procesando '%s'. Captura de depuracion: %s", filename, screenshot_path)
        except Exception as exc:
            log.error("Fallo procesando '%s' y no se pudo guardar captura: %s", filename, exc)
