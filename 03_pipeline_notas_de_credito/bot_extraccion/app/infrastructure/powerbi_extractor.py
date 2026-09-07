"""
Adaptador de infraestructura: implementa el puerto ReportExtractor usando
Playwright contra Power BI Service. Toda la lógica específica de Power BI
(selectores, virtualización de visuales, menús) vive aquí -- las capas
superiores (application/domain) no conocen Playwright.

Implementa el protocolo ReportExtractor de app.application.ports.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from app.domain.exceptions import AutenticacionError, DescargaError, VisualNoEncontradoError
from app.domain.models import ExportSettings
from app.infrastructure.diagnostics import diagnosticar_pagina
from app.infrastructure.logging_setup import NOMBRE_LOGGER

logger = logging.getLogger(NOMBRE_LOGGER)


class PowerBiDetalleNCExtractor:
    """Etapa 'Extract': autentica, navega y exporta la tabla configurada desde Power BI."""

    def __init__(self, page: Page, settings: ExportSettings, diagnose: bool = False) -> None:
        self._page = page
        self._settings = settings
        self._diagnose = diagnose

    # -- Punto de entrada del puerto ReportExtractor ------------------------

    def extraer(self) -> Path:
        self._abrir_informe()
        if self._diagnose:
            diagnosticar_pagina(self._page)
        self._navegar_a_pagina_objetivo()
        self._aplicar_filtros()
        contenedor = self._localizar_tabla()
        self._abrir_menu_opciones(contenedor)
        return self._exportar_datos()

    # -- Autenticación / carga del informe -----------------------------------

    def _abrir_informe(self) -> None:
        self.navegar_al_informe()
        self._esperar_autenticacion()
        logger.info("Informe cargado correctamente.")

    def navegar_al_informe(self) -> None:
        """
        Navega a la URL del informe (sin esperar autenticación). Público
        para que main.py pueda hacer un sondeo rápido de sesión -- con
        HEADLESS=true no tiene sentido esperar un login que nadie puede
        completar sin ventana visible, así que primero hay que averiguar si
        hace falta antes de decidir con qué modo (headless o no) continuar.
        """
        self._page.goto(
            self._settings.report_url,
            wait_until="domcontentloaded",
            timeout=self._settings.nav_timeout,
        )

    def hay_pantalla_login(self, timeout_ms: int = 8_000) -> bool:
        """
        Comprobación corta (no bloqueante para el usuario): ¿Power BI está
        mostrando el login de Microsoft en este momento? No espera a que se
        complete, solo detecta si está presente.
        """
        # input de email/usuario del login de Microsoft (id estable históricamente).
        login_indicator = self._page.locator("input[type='email'], input[name='loginfmt'], #i0116")
        try:
            login_indicator.first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            return False

    def esperar_login_manual(self) -> None:
        """Espera (polling, hasta login_poll_timeout) a que el usuario complete
        el login manualmente y el informe quede cargado. Requiere un
        navegador visible -- quien orquesta el fallback headless/visible es
        main.py."""
        logger.info(
            "Se requiere iniciar sesión manualmente. Completa el login en la "
            "ventana del navegador; el script continuará solo cuando el "
            "informe cargue."
        )
        self._esperar_carga_informe(timeout=self._settings.login_poll_timeout)

    def _esperar_autenticacion(self) -> None:
        """
        Si Power BI muestra el login de Microsoft, se detiene aquí y espera
        (hasta login_poll_timeout) a que el usuario inicie sesión
        manualmente. Si ya hay sesión activa, sigue de largo.
        """
        logger.info("Verificando autenticación...")
        if self.hay_pantalla_login():
            self.esperar_login_manual()
        else:
            self._esperar_carga_informe(timeout=self._settings.login_poll_timeout)

    def _esperar_carga_informe(self, timeout: int) -> None:
        """
        Espera a que el informe esté interactivo. Señal usada: el panel de
        navegación de páginas (izquierda) queda visible con al menos una
        pestaña. Se probaron varias estrategias porque la clase CSS del
        'canvas' del informe cambia entre versiones de Power BI; el rol de
        accesibilidad 'tab' de las páginas es mucho más estable.
        """
        page = self._page
        candidatos = [
            page.get_by_role("tab"),
            page.get_by_role("listitem").filter(has_text=self._settings.report_page_name),
            page.get_by_text(self._settings.report_page_name, exact=True),
        ]
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            for candidato in candidatos:
                try:
                    if candidato.count() > 0 and candidato.first.is_visible():
                        return
                except Exception:
                    continue
            time.sleep(1)

        raise AutenticacionError(
            "El informe no terminó de cargar a tiempo (¿sigue pendiente el "
            f"login, o la URL/permiso del informe cambió?). URL actual: {page.url}"
        )

    def _esperar_visuales_cargados(self, timeout: Optional[int] = None) -> None:
        """
        Power BI no expone un evento único de 'todos los visuales listos',
        así que se usa como señal la presencia de al menos un contenedor de
        visual renderizado en la página actual.
        """
        timeout = timeout or self._settings.visual_timeout
        visual = self._page.locator(
            "[class*='visualContainerHost'], [class*='visual-container-component']"
        ).first
        try:
            visual.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            logger.warning("No se detectaron visuales tras la espera; se continúa igualmente.")

    # -- Navegación -----------------------------------------------------------

    def _buscar_pestana(self, nombre: str) -> Optional[Locator]:
        """
        Busca la pestaña de página del informe priorizando el rol de
        accesibilidad ('tab'), que es más estable que las clases CSS.
        """
        page = self._page
        candidatos = [
            page.get_by_role("tab", name=nombre, exact=False),
            page.locator(f"[aria-label='{nombre}']"),
            page.get_by_text(nombre, exact=True),
        ]
        for candidato in candidatos:
            try:
                if candidato.count() > 0:
                    candidato.first.wait_for(state="visible", timeout=10_000)
                    return candidato.first
            except PlaywrightTimeoutError:
                continue
        return None

    def _navegar_a_pagina_objetivo(self) -> None:
        nombre_pagina = self._settings.report_page_name
        logger.info(f"Navegando a {nombre_pagina}...")
        tab = self._buscar_pestana(nombre_pagina)
        if tab is None:
            raise VisualNoEncontradoError(
                f"No se encontró la pestaña de página '{nombre_pagina}'. "
                "Ejecuta con --diagnose para ver qué pestañas detecta el script."
            )
        tab.scroll_into_view_if_needed()
        tab.click()
        self._esperar_visuales_cargados()

    # -- Filtros (slicers) ------------------------------------------------------

    def _contenedor_de_slicer(self, titulo_visible: str) -> Locator:
        """
        Ubica el contenedor de un slicer a partir de su título visible
        (h3.slicer-header-text). OJO: el 'aria-label' del combobox interno
        es el nombre del CAMPO de datos (ej. 'EMPRESA'), no el título visible
        del slicer (ej. 'PROVEEDOR') -- confirmado inspeccionando el DOM en
        vivo. Por eso no se puede buscar el combobox por su propio
        aria-label; hay que subir desde el título visible como con la tabla.
        """
        titulo = self._page.locator(
            "h3.slicer-header-text",
            has_text=re.compile(rf"^\s*{re.escape(titulo_visible)}\s*$"),
        ).first
        contenedor = titulo.locator(
            "xpath=ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' visual-container-component ')][1]"
        ).first
        if contenedor.count() == 0:
            raise VisualNoEncontradoError(
                f"No se encontró el filtro '{titulo_visible}' en la página "
                f"'{self._settings.report_page_name}'. Ejecuta con --diagnose "
                "para revisar los filtros detectados."
            )
        return contenedor

    def _aplicar_filtros(self) -> None:
        """Aplica los filtros configurables (.env) antes de exportar la tabla."""
        self._aplicar_filtro_anio(self._settings.filtro_anio)
        self._aplicar_filtro_dropdown("MES NC", self._settings.filtro_mes_nc)
        self._aplicar_filtro_dropdown("PROVEEDOR", self._settings.filtro_proveedor)
        # Deja que el informe recalcule los visuales tras aplicar los filtros
        # antes de seguir con la localización/exportación de la tabla.
        self._page.wait_for_timeout(1_000)

    def _aplicar_filtro_anio(self, valor: str) -> None:
        """
        El slicer 'AÑO NC' es de tipo "tabular"/chiclet: solo muestra 2 años
        a la vez y hay que ir pulsando el botón 'Siguiente' hasta que
        aparezca el año buscado (confirmado en vivo: por defecto muestra los
        años más antiguos, 2023/2024).
        """
        if not valor:
            return
        logger.info(f"Aplicando filtro AÑO NC = {valor}...")
        contenedor = self._contenedor_de_slicer("AÑO NC")
        boton_siguiente = contenedor.get_by_role("button", name="Siguiente")
        opcion = contenedor.get_by_role("option", name=valor, exact=True)

        intentos = 0
        while intentos < 20:
            if opcion.count() > 0 and opcion.first.is_visible():
                # Los slicers de Power BI son de tipo toggle: si la opción ya
                # está seleccionada, un clic la DESELECCIONA (deja el filtro
                # en "Todas") en vez de confirmarla. Solo se hace clic si
                # todavía no está seleccionada.
                if opcion.first.get_attribute("aria-selected") == "true":
                    logger.info(f"AÑO NC ya estaba en {valor}; no se toca.")
                else:
                    opcion.first.click()
                return
            if boton_siguiente.count() == 0:
                break
            boton_siguiente.first.click()
            self._page.wait_for_timeout(250)
            intentos += 1

        raise VisualNoEncontradoError(
            f"No se encontró el año '{valor}' en el filtro AÑO NC tras "
            "desplazar la barra de años. Ejecuta con --diagnose para revisar "
            "los años disponibles."
        )

    def _aplicar_filtro_dropdown(self, titulo_visible: str, valor: str) -> None:
        """
        Slicers de tipo lista desplegable (combobox): MES NC, PROVEEDOR, etc.
        El buscador interno es opcional -- algunos slicers lo traen
        deshabilitado (confirmado en vivo con PROVEEDOR, que solo tiene 3
        opciones y no lo necesita), así que se usa solo si está disponible.
        """
        if not valor:
            return
        logger.info(f"Aplicando filtro {titulo_visible} = {valor}...")
        page = self._page
        contenedor = self._contenedor_de_slicer(titulo_visible)
        combobox = contenedor.locator('[role="combobox"]')
        try:
            combobox.first.wait_for(state="visible", timeout=self._settings.menu_timeout)
        except PlaywrightTimeoutError as exc:
            raise VisualNoEncontradoError(
                f"No se encontró el control desplegable del filtro "
                f"'{titulo_visible}'. Ejecuta con --diagnose para revisar."
            ) from exc
        combobox.first.click()
        page.wait_for_timeout(300)

        popup_id = combobox.first.get_attribute("aria-controls")
        popup = page.locator(f"#{popup_id}") if popup_id else page.locator(".slicer-dropdown-popup")

        # Buscador opcional: si existe y es usable, filtra la lista (útil en
        # slicers con muchas opciones). Si no, se sigue sin filtrar.
        buscador = popup.locator("input.searchInput")
        if buscador.count() > 0:
            try:
                if not buscador.first.is_visible():
                    popup.locator(".searchHeader").first.click(timeout=1_000)
                if buscador.first.is_visible():
                    buscador.first.fill(valor)
                    page.wait_for_timeout(400)
            except Exception:
                pass  # este slicer no tiene buscador habilitado; se sigue sin filtrar

        opcion = popup.locator("[role='option']").filter(
            has_text=re.compile(rf"^\s*{re.escape(valor)}\s*$")
        )
        try:
            opcion.first.wait_for(state="visible", timeout=self._settings.menu_timeout)
        except PlaywrightTimeoutError as exc:
            page.keyboard.press("Escape")
            raise VisualNoEncontradoError(
                f"No se encontró la opción '{valor}' dentro del filtro "
                f"'{titulo_visible}'. Ejecuta con --diagnose para revisar los "
                "valores disponibles."
            ) from exc
        # Los slicers de Power BI son de tipo toggle: si la opción ya está
        # seleccionada, un clic la DESELECCIONA (deja el filtro en "Todas")
        # en vez de confirmarla. Solo se hace clic si todavía no lo está.
        if opcion.first.get_attribute("aria-selected") == "true":
            logger.info(f"{titulo_visible} ya estaba en {valor}; no se toca.")
        else:
            opcion.first.click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

    # -- Localización de la tabla ----------------------------------------------

    def _titulos_candidatos(self, nombre: str) -> list[Locator]:
        """
        Devuelve TODOS los elementos candidatos a título de visual con el
        texto dado. Power BI suele duplicar el título (un nodo visible + un
        nodo de accesibilidad oculto para lectores de pantalla), por lo que
        tomar solo el primer match puede agarrar el duplicado invisible;
        probamos todos.
        """
        page = self._page
        resultado: list[Locator] = []
        estrategias = [
            page.locator(f"[title='{nombre}']"),
            page.get_by_text(nombre, exact=True),
            page.locator(f"[aria-label='{nombre}']"),
        ]
        for candidato in estrategias:
            try:
                total = candidato.count()
            except Exception:
                continue
            for i in range(total):
                resultado.append(candidato.nth(i))
        return resultado

    def _localizar_tabla(self) -> Locator:
        """
        Estrategia: texto/título de la tabla objetivo -> se sube por el DOM
        (XPath ancestor) hasta el contenedor del visual (clase que contenga
        'visualContainerHost' o 'visual-container-component'). Subir desde
        el texto encontrado, en vez de asumir un contenedor fijo, evita
        agarrar el "..." de otro visual distinto que esté cerca en la
        página. Se prueban todos los títulos candidatos hasta dar con uno
        cuyo contenedor realmente se pueda desplegar en pantalla.
        """
        nombre_tabla = self._settings.table_visual_name
        logger.info(f"Buscando tabla {nombre_tabla}...")
        titulos = self._titulos_candidatos(nombre_tabla)
        if not titulos:
            raise VisualNoEncontradoError(
                f"No se encontró el visual '{nombre_tabla}' en la página "
                f"'{self._settings.report_page_name}'. Ejecuta con --diagnose "
                "para ver los títulos de visual detectados."
            )

        for titulo in titulos:
            contenedor = titulo.locator(
                "xpath=ancestor::*["
                "contains(concat(' ', normalize-space(@class), ' '), ' visualContainerHost ')"
                " or contains(concat(' ', normalize-space(@class), ' '), ' visual-container-component ')"
                "][1]"
            )
            if contenedor.count() == 0:
                continue
            contenedor = contenedor.first
            try:
                # OJO: <visual-container> es un elemento 'display: inline'
                # cuyo propio bounding box puede ser 0x0 aunque su contenido
                # (título, tabla) tenga tamaño real -- confirmado
                # inspeccionando el DOM en vivo. Por eso el desplazamiento/
                # visibilidad se valida sobre 'titulo' (que sí tiene
                # geometría real), no sobre 'contenedor'.
                self._desplazar_hasta_visible(titulo, intentos=15)
                logger.info("Tabla encontrada.")
                return contenedor
            except VisualNoEncontradoError:
                continue  # este candidato no resultó ser el visual real; probar el siguiente

        raise VisualNoEncontradoError(
            f"Se encontraron {len(titulos)} elemento(s) con el texto "
            f"'{nombre_tabla}' pero ninguno resultó ser un visual visible "
            "en pantalla. Ejecuta con --diagnose e inspecciona el DOM manualmente."
        )

    def _desplazar_hasta_visible(self, locator: Locator, intentos: int = 40, paso_px: int = 350) -> None:
        """
        Power BI virtualiza los visuales fuera de la vista:
        'scroll_into_view_if_needed' mueve el scroll a nivel DOM pero no
        siempre dispara la detección de redimensionado interna de Power BI,
        y el visual queda con tamaño 0 (no 'visible' para Playwright). Por
        eso se simula scroll real con la rueda del mouse, que sí dispara
        esos eventos, reintentando hasta que el elemento quede realmente
        visible.
        """
        page = self._page
        viewport = page.viewport_size or {"width": 1600, "height": 900}
        page.mouse.move(viewport["width"] / 2, viewport["height"] / 2)
        try:
            locator.scroll_into_view_if_needed(timeout=5_000)
        except Exception:
            pass
        for _ in range(intentos):
            try:
                if locator.is_visible():
                    return
            except Exception:
                pass
            page.mouse.wheel(0, paso_px)
            page.wait_for_timeout(200)
        if not locator.is_visible():
            raise VisualNoEncontradoError(
                f"No se pudo desplazar la vista hasta que el visual "
                f"'{self._settings.table_visual_name}' quedara visible."
            )

    def _abrir_menu_opciones(self, contenedor: Locator) -> None:
        """
        El botón de "más opciones" (...) suele quedar oculto
        (opacity/visibility) hasta que el visual recibe hover; por eso se
        hace hover explícito antes de buscarlo. Se busca dentro de
        'contenedor' (no en toda la página) para garantizar que corresponde
        EXCLUSIVAMENTE al visual objetivo.

        'contenedor' (<visual-container>) puede tener bounding box 0x0 (ver
        nota en _localizar_tabla), así que el hover se hace sobre su título
        (con geometría real) -- el estado :hover se propaga igual a
        'contenedor' porque el título es descendiente suyo.
        """
        logger.info("Abriendo menú de la tabla...")
        ancla_candidatos = contenedor.locator(
            "[class*='visualTitle'], h3[class*='preTextWithEllipsis']"
        )
        ancla = ancla_candidatos.first if ancla_candidatos.count() > 0 else contenedor
        self._desplazar_hasta_visible(ancla)
        ancla.hover()

        boton = contenedor.locator(
            "button[aria-label='More options' i], "
            "button[aria-label='Más opciones' i], "
            "button[title='More options' i], "
            "button[title='Más opciones' i]"
        )
        try:
            boton.first.wait_for(state="visible", timeout=self._settings.menu_timeout)
        except PlaywrightTimeoutError as exc:
            raise VisualNoEncontradoError(
                "No se encontró el botón de opciones (...) para "
                f"'{self._settings.table_visual_name}'. Puede que Power BI "
                "haya cambiado el aria-label del botón; ejecuta con --diagnose."
            ) from exc
        boton.first.click()

    # -- Exportación / descarga ----------------------------------------------

    def _exportar_datos(self) -> Path:
        """
        Tras abrir el menú "...", selecciona "Exportar datos", luego "Datos
        con diseño actual" y confirma con "Exportar", capturando la
        descarga y guardándola en un archivo temporal (descargas_dir).

        El menú contextual y el diálogo de exportación se renderizan en una
        capa global (no dentro del contenedor del visual), por eso aquí se
        busca en 'page' completo — ya no hay ambigüedad porque solo puede
        haber un menú/diálogo abierto a la vez.
        """
        page = self._page
        timeout = self._settings.menu_timeout

        logger.info("Seleccionando Exportar datos...")
        item_exportar = page.get_by_role(
            "menuitem", name=re.compile(r"export data|exportar datos", re.I)
        )
        try:
            item_exportar.first.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError as exc:
            raise DescargaError(
                "No apareció la opción 'Exportar datos' en el menú contextual "
                "(¿el usuario tiene permiso de exportación en este informe?)."
            ) from exc
        item_exportar.first.click()

        logger.info("Seleccionando Datos con diseño actual...")
        opcion_layout = page.get_by_text(re.compile(r"current layout|diseño actual", re.I))
        try:
            opcion_layout.first.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError as exc:
            raise DescargaError(
                "No apareció la opción 'Datos con diseño actual' en el diálogo "
                "de exportación."
            ) from exc
        opcion_layout.first.click()

        boton_exportar = page.get_by_role("button", name=re.compile(r"^export$|^exportar$", re.I))
        try:
            boton_exportar.first.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError as exc:
            raise DescargaError("No apareció el botón 'Exportar' del diálogo.") from exc

        logger.info("Iniciando descarga...")
        with page.expect_download(timeout=self._settings.download_timeout) as download_info:
            boton_exportar.first.click()
        download = download_info.value
        logger.info("Archivo descargado correctamente.")

        self._settings.descargas_dir.mkdir(parents=True, exist_ok=True)
        archivo_temporal = self._settings.descargas_dir / download.suggested_filename
        download.save_as(str(archivo_temporal))
        return archivo_temporal
