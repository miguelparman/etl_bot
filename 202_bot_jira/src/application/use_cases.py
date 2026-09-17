"""Caso de uso: registrar/actualizar worklogs en Jira a partir de la plantilla."""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from ..domain.exceptions import DomainError
from ..domain.models import WorklogOutcome, WorklogRow
from ..domain.value_objects import Ticket, started_from_raw, time_spent_from_raw
from .ports import JiraWorklogGateway, WorklogRepository

ProgressCallback = Callable[[WorklogRow, WorklogOutcome], None]


@dataclass
class RegistroSummary:
    ok: int = 0
    ko: int = 0
    saltados: int = 0

    def __str__(self) -> str:
        return f"Registrados: {self.ok} | Errores: {self.ko} | Ya registrados (saltados): {self.saltados}"


class RegistrarWorklogsUseCase:
    def __init__(
        self,
        repository: WorklogRepository,
        jira: JiraWorklogGateway,
        tz: ZoneInfo,
        on_row_processed: Optional[ProgressCallback] = None,
    ):
        self._repository = repository
        self._jira = jira
        self._tz = tz
        self._on_row_processed = on_row_processed

    def execute(self) -> RegistroSummary:
        summary = RegistroSummary()

        for row in self._repository.load():
            outcome = self._procesar_fila(row)
            self._repository.record_outcome(row, outcome)
            if self._on_row_processed is not None:
                self._on_row_processed(row, outcome)
            if outcome.skipped:
                summary.saltados += 1
            elif outcome.ok:
                summary.ok += 1
            else:
                summary.ko += 1

        self._repository.save()
        return summary

    def _procesar_fila(self, row: WorklogRow) -> WorklogOutcome:
        """Crea o actualiza el worklog de una fila según la columna 'Accion'.

        - Accion != 'Actualizar': se crea un worklog nuevo, salvo que la fila
          ya tenga 'Registrado' empezando por 'Sí' (se salta para no duplicar).
        - Accion == 'Actualizar': se actualiza el worklog existente. Requiere
          que la fila tenga un WorklogID guardado (el que quedó al crearlo la
          primera vez); si falta, se reporta error sin llamar a Jira. Además,
          en este modo NO se salta aunque 'Registrado' ya diga 'Sí'.
        """
        try:
            ticket = Ticket.parse(row.ticket_raw)
        except DomainError:
            return WorklogOutcome(registrado="Error: ticket inválido")

        es_actualizacion = row.es_actualizacion

        if not es_actualizacion and row.ya_registrado:
            return WorklogOutcome(registrado=row.registrado, skipped=True)

        worklog_id = row.worklog_id.strip()
        if es_actualizacion and (not worklog_id or worklog_id.lower() == "nan"):
            return WorklogOutcome(registrado="Error: no hay WorklogID guardado para actualizar esta fila")

        try:
            started = started_from_raw(row.fecha, self._tz)
            time_spent = time_spent_from_raw(row.horas)
            if es_actualizacion:
                resultado = self._jira.update(str(ticket), worklog_id, started, time_spent, row.comentario)
            else:
                resultado = self._jira.create(str(ticket), started, time_spent, row.comentario)
        except Exception as exc:
            return WorklogOutcome(registrado=f"Error: {exc}")

        if not resultado.success:
            return WorklogOutcome(registrado=f"Error: {resultado.error_message}")

        ahora = datetime.now(self._tz).strftime("%d/%m/%Y %H:%M")
        if es_actualizacion:
            return WorklogOutcome(registrado=f"Sí (actualizado {ahora})", accion="", ok=True)
        return WorklogOutcome(registrado=f"Sí ({ahora})", worklog_id=resultado.worklog_id or "", ok=True)
