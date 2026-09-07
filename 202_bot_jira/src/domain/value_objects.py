"""Objetos de valor y reglas de negocio puras (sin I/O)."""

import re
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .exceptions import InvalidTicketError, InvalidTimeFormatError

_TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


@dataclass(frozen=True)
class Ticket:
    code: str

    @classmethod
    def parse(cls, raw) -> "Ticket":
        code = str(raw).strip().upper()
        if not _TICKET_RE.match(code):
            raise InvalidTicketError(f"Ticket inválido: {raw!r}")
        return cls(code)

    def __str__(self) -> str:
        return self.code


def time_spent_from_raw(valor) -> str:
    """Convierte un valor de horas (texto 'HH:MM' o time/datetime) al formato timeSpent de Jira."""
    if isinstance(valor, str):
        texto = valor.strip()
        if ":" not in texto:
            return texto
        horas, minutos = (int(x) for x in texto.split(":")[:2])
    elif isinstance(valor, (time, datetime)):
        horas, minutos = valor.hour, valor.minute
    else:
        raise InvalidTimeFormatError(f"Formato de horas no soportado: {valor!r} (usa HH:MM)")

    partes = []
    if horas:
        partes.append(f"{horas}h")
    if minutos or not partes:
        partes.append(f"{minutos}m")
    return " ".join(partes)


def started_from_raw(valor, tz: ZoneInfo) -> str:
    """Convierte una fecha (datetime o texto dd/mm/aaaa[ HH:MM[:SS]]) al formato 'started' de Jira."""
    if isinstance(valor, datetime):
        fecha = valor
    else:
        texto = str(valor).strip()
        try:
            fecha = datetime.strptime(texto, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            fecha = datetime.strptime(texto, "%d/%m/%Y %H:%M")
    fecha = fecha.replace(tzinfo=tz)
    return fecha.strftime("%Y-%m-%dT%H:%M:%S.000%z")
