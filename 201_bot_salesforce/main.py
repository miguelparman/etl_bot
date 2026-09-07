"""
Punto de entrada de la automatizacion Salesforce -> SharePoint.

Uso:
    python main.py                (interactivo, con consola)
    pythonw.exe main.py           (desatendido/programado, sin consola)

Estado actual (Fase 10): ademas de la integracion completa (Fases 7-9),
preparado para ejecucion desatendida via Windows Task Scheduler: el logger
funciona sin consola (pythonw.exe deja sys.stdout/sys.stderr en None), y
cualquier fallo durante el arranque (antes de que exista el logger, p.ej.
un .env mal configurado) queda registrado en logs/startup_error.log en vez
de perderse en silencio. La creacion de la tarea programada en si (Trigger,
Accion, etc.) es un paso manual documentado en README.md -- no se
automatiza aqui.
"""

from __future__ import annotations

import sys

try:
    from app.config import settings
    from app.logger import log
    from app.salesforce.client import SalesforceClient
    from app.services.local_delivery import LocalDeliveryCopier
    from app.services.orchestrator import ReportOrchestrator, format_summary
    from app.services.retry import retry_call
    from app.sharepoint.auth import get_graph_token
    from app.sharepoint.client import SharePointClient, SharePointFolderResolver
    from app.sharepoint.uploader import SharePointUploader
    from config.reports import REPORTS
except Exception:
    # Sin esto, un fallo de configuracion (p.ej. falta una variable en
    # .env) durante una ejecucion desatendida con pythonw.exe (sin consola)
    # se perderia por completo: no hay stdout/stderr visibles y el logger
    # normal (app.logger) todavia no llego a inicializarse.
    import traceback
    from datetime import datetime
    from pathlib import Path

    fallback_dir = Path(__file__).resolve().parent / "logs"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    with open(fallback_dir / "startup_error.log", "a", encoding="utf-8") as fh:
        fh.write(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} | Fallo al iniciar la aplicacion:\n")
        fh.write(traceback.format_exc())
    raise


def main() -> int:
    log.info("=" * 50)
    log.info("SALESFORCE -> SHAREPOINT AUTOMATION")
    log.info("=" * 50)
    log.info("Configuracion cargada correctamente.")
    log.info(
        "Modo headless: %s | DRY_RUN: %s | MAX_REPORTS: %s",
        settings.headless,
        settings.dry_run,
        settings.max_reports or "todos",
    )

    uploader = None
    folder_resolver = None
    local_copier = None
    if settings.dry_run:
        log.warning("DRY_RUN=true: no se autentica contra Graph ni se copia/sube nada.")
    else:
        local_copier = LocalDeliveryCopier(
            destination_dir=settings.local_copy_dir,
            overwrite=settings.overwrite_existing,
        )

        log.info("Autenticando contra Microsoft Graph...")
        token = retry_call(
            lambda: get_graph_token(
                tenant_id=settings.tenant_id,
                client_id=settings.client_id,
                client_secret=settings.client_secret,
                timeout_ms=settings.graph_timeout_ms,
            ),
            max_retries=settings.max_retries,
            what="Autenticacion en Microsoft Graph",
        )

        sharepoint_client = SharePointClient(token=token, timeout_ms=settings.graph_timeout_ms)
        target = retry_call(
            lambda: sharepoint_client.resolve_target(
                hostname=settings.sharepoint_hostname,
                site_path=settings.sharepoint_site_path,
                drive_name=settings.sharepoint_drive_name,
                folder_path=settings.sharepoint_folder_path,
                cached_site_id=settings.sharepoint_site_id,
                cached_drive_id=settings.sharepoint_drive_id,
                cached_folder_id=settings.sharepoint_folder_id,
            ),
            max_retries=settings.max_retries,
            what="Resolucion de site/drive/carpeta en SharePoint",
        )

        uploader = SharePointUploader(
            token=token,
            drive_id=target.drive_id,
            default_folder_id=target.folder_id,
            timeout_ms=settings.graph_timeout_ms,
            overwrite=settings.overwrite_existing,
        )
        folder_resolver = SharePointFolderResolver(
            client=sharepoint_client,
            drive_id=target.drive_id,
            default_folder_id=target.folder_id,
        )

    with SalesforceClient(
        domain=settings.salesforce_domain,
        username=settings.salesforce_username,
        password=settings.salesforce_password,
        auth_state_path=settings.auth_state_path,
        manual_login_timeout_minutes=settings.manual_login_timeout_minutes,
        page_timeout_ms=settings.page_timeout_ms,
        headless=settings.headless,
    ) as sf_client:
        log.info("Sesion de Salesforce lista.")

        orchestrator = ReportOrchestrator(
            sf_client=sf_client,
            sharepoint_uploader=uploader,
            folder_resolver=folder_resolver,
            local_copier=local_copier,
            settings=settings,
        )
        summary = orchestrator.run(REPORTS)

    log.info(format_summary(summary))
    return 1 if summary.failed else 0


if __name__ == "__main__":
    sys.exit(main())
