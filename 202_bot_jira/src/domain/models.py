"""Entidades de dominio: una fila de la plantilla y el resultado de procesarla."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorklogRow:
    """Una fila de la plantilla Excel, tal como fue leída."""

    index: int
    ticket_raw: object
    fecha: object
    horas: object
    comentario: object
    accion: str
    registrado: str
    worklog_id: str

    @property
    def es_actualizacion(self) -> bool:
        """True si la columna 'Accion' del Excel dice 'Actualizar' (case-insensitive).

        Esta convención es lo que decide si el caso de uso llama a
        JiraWorklogGateway.update en vez de .create; ver
        RegistrarWorklogsUseCase._procesar_fila.
        """
        return self.accion.strip().lower() == "actualizar"

    @property
    def ya_registrado(self) -> bool:
        return self.registrado.strip().lower().startswith("sí")


@dataclass
class WorklogOutcome:
    """Resultado de procesar una fila: qué escribir de vuelta en el Excel."""

    registrado: str
    accion: Optional[str] = None
    worklog_id: Optional[str] = None
    ok: bool = False
    skipped: bool = False
