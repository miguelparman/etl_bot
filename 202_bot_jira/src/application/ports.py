"""Puertos (interfaces) que la capa de aplicación espera de la infraestructura."""

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..domain.models import WorklogOutcome, WorklogRow


@dataclass
class JiraWorklogResult:
    """Resultado, ya interpretado, de una llamada a la API de Jira."""

    success: bool
    worklog_id: Optional[str] = None
    error_message: Optional[str] = None


class WorklogRepository(Protocol):
    def load(self) -> List[WorklogRow]: ...

    def record_outcome(self, row: WorklogRow, outcome: WorklogOutcome) -> None: ...

    def save(self) -> None: ...


class JiraWorklogGateway(Protocol):
    def create(self, ticket: str, started: str, time_spent: str, comentario: str) -> JiraWorklogResult: ...

    def update(
        self, ticket: str, worklog_id: str, started: str, time_spent: str, comentario: str
    ) -> JiraWorklogResult: ...
