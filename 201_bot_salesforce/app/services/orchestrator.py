"""
ReportOrchestrator: coordina Salesforce -> descarga -> validacion ->
SharePoint -> resultado, para la lista completa de config/reports.py.

Responsabilidades:
- Recorrer REPORTS (respetando MAX_REPORTS) sin detenerse ante un error
  individual.
- Aplicar DRY_RUN (exportar y validar, sin copiar ni subir a ningun lado).
- Copiar cada informe a una carpeta local/de red adicional (local_copier),
  sumado a la subida a SharePoint. Un fallo en esa copia adicional se
  registra pero NO aborta el reporte: SharePoint sigue siendo la entrega
  principal.
- Cada informe puede declarar opcionalmente su propia subcarpeta de
  SharePoint ("sharepoint_folder_path") y/o su propia carpeta local
  ("local_copy_dir") en config/reports.py; si no lo hace, se usa el
  destino global por defecto.
- Aplicar DELETE_LOCAL_AFTER_UPLOAD solo tras una subida a SharePoint
  confirmada (la copia local adicional, si existe, ya es permanente por si
  sola y no depende de este flag).
- Acumular resultados y construir el resumen final (correctos/errores).

Cada informe se reintenta (MAX_RETRIES, con backoff) como dos unidades
independientes: la exportacion completa (navegacion + carga + exportacion +
descarga, ya que todas parten de un page.goto fresco al reintentar) y la
subida a SharePoint por separado -- asi un fallo transitorio de Graph no
obliga a re-exportar el informe desde Salesforce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.logger import log
from app.salesforce.exporter import SalesforceReportExporter
from app.services.retry import retry_call

_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _format_hms(elapsed: timedelta) -> str:
    total_seconds = int(elapsed.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_dhm(elapsed: timedelta) -> str:
    total_seconds = int(elapsed.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days} dia(s), {hours} hora(s), {minutes} minuto(s)"


@dataclass
class ReportResult:
    name: str
    success: bool
    error: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def elapsed(self) -> timedelta:
        if self.start_time is None or self.end_time is None:
            return timedelta(0)
        return self.end_time - self.start_time


@dataclass
class ExecutionSummary:
    results: list[ReportResult] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> list[ReportResult]:
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[ReportResult]:
        return [r for r in self.results if not r.success]

    @property
    def elapsed(self) -> timedelta:
        if self.start_time is None or self.end_time is None:
            return timedelta(0)
        return self.end_time - self.start_time


def _format_result_line(marker: str, r: ReportResult) -> list[str]:
    inicio = r.start_time.strftime(_TIMESTAMP_FORMAT) if r.start_time else "-"
    fin = r.end_time.strftime(_TIMESTAMP_FORMAT) if r.end_time else "-"
    lines = [
        f"{marker} {r.name}",
        f"    Inicio: {inicio} | Fin: {fin} | Duracion: {_format_hms(r.elapsed)}",
    ]
    if not r.success:
        lines.append(f"    Error: {r.error}")
    return lines


def format_summary(summary: ExecutionSummary) -> str:
    lines = [
        "=" * 40,
        "RESUMEN DE EJECUCION",
        "=" * 40,
        "",
        f"Total: {summary.total}",
        f"Correctos: {len(summary.succeeded)}",
        f"Errores: {len(summary.failed)}",
        "",
    ]
    if summary.succeeded:
        lines.append("CORRECTOS:")
        for r in summary.succeeded:
            lines.extend(_format_result_line("✓", r))
        lines.append("")
    if summary.failed:
        lines.append("ERRORES:")
        for r in summary.failed:
            lines.extend(_format_result_line("✗", r))
        lines.append("")
    lines.append("=" * 40)
    lines.append("TIEMPO TOTAL DEL PROCESO")
    lines.append("=" * 40)
    inicio_global = summary.start_time.strftime(_TIMESTAMP_FORMAT) if summary.start_time else "-"
    fin_global = summary.end_time.strftime(_TIMESTAMP_FORMAT) if summary.end_time else "-"
    lines.append(f"Inicio: {inicio_global}")
    lines.append(f"Fin: {fin_global}")
    lines.append(f"Duracion: {_format_dhm(summary.elapsed)}")
    lines.append("=" * 40)
    return "\n".join(lines)


class ReportOrchestrator:
    def __init__(self, sf_client, sharepoint_uploader, folder_resolver, local_copier, settings) -> None:
        self._sf_client = sf_client
        self._sharepoint_uploader = sharepoint_uploader
        self._folder_resolver = folder_resolver
        self._local_copier = local_copier
        self._settings = settings

    def run(self, reports: list[dict]) -> ExecutionSummary:
        selected = reports[: self._settings.max_reports] if self._settings.max_reports else reports
        summary = ExecutionSummary()
        summary.start_time = datetime.now()

        for index, report in enumerate(selected, start=1):
            name = report["name"]
            log.info("[%02d/%02d] %s", index, len(selected), name)
            report_start = datetime.now()
            try:
                self._process_one(report)
                report_end = datetime.now()
                summary.results.append(
                    ReportResult(name=name, success=True, start_time=report_start, end_time=report_end)
                )
                log.info("  OK")
            except Exception as exc:
                report_end = datetime.now()
                summary.results.append(
                    ReportResult(
                        name=name,
                        success=False,
                        error=str(exc),
                        start_time=report_start,
                        end_time=report_end,
                    )
                )
                log.exception("  Error procesando '%s'", name)

        summary.end_time = datetime.now()
        return summary

    def _process_one(self, report: dict) -> None:
        name = report["name"]
        page = self._sf_client.new_page()
        try:
            exporter = SalesforceReportExporter(
                page=page,
                downloads_dir=self._settings.downloads_dir,
                screenshots_dir=self._settings.screenshots_dir,
                download_timeout_ms=self._settings.download_timeout_ms,
            )
            local_path = retry_call(
                lambda: exporter.export_report(report["url"], name),
                max_retries=self._settings.max_retries,
                what=f"Exportacion de '{name}'",
            )
        finally:
            page.close()

        if self._settings.dry_run:
            log.info("  DRY_RUN=true: no se copia ni se sube a ningun destino.")
            return

        local_dir_override = report.get("local_copy_dir")
        destination_dir = Path(local_dir_override) if local_dir_override else None
        try:
            retry_call(
                lambda: self._local_copier.copy(local_path, destination_dir=destination_dir),
                max_retries=self._settings.max_retries,
                what=f"Copia local adicional de '{name}'",
            )
        except Exception:
            # Entrega secundaria: no debe impedir que se intente la subida
            # a SharePoint, que es la entrega principal del proceso.
            log.exception("  No se pudo copiar '%s' a la carpeta local adicional; se continua con SharePoint.", name)

        folder_path_override = report.get("sharepoint_folder_path")
        folder_id = retry_call(
            lambda: self._folder_resolver.resolve(folder_path_override),
            max_retries=self._settings.max_retries,
            what=f"Resolucion de carpeta SharePoint para '{name}'",
        )
        uploaded = retry_call(
            lambda: self._sharepoint_uploader.upload(local_path, folder_id=folder_id),
            max_retries=self._settings.max_retries,
            what=f"Subida de '{name}' a SharePoint",
        )
        if uploaded and self._settings.delete_local_after_upload:
            local_path.unlink()
            log.info("  Archivo local eliminado tras la subida.")
