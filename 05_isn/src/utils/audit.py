"""Conteo y resumen de auditoria del ETL (seccion 9 del requerimiento:
inicio/fin, duracion, registros extraidos/transformados/cargados/rechazados)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunAudit:
    started_at: float = field(default_factory=time.monotonic)
    extracted: dict[str, int] = field(default_factory=dict)
    loaded: dict[str, int] = field(default_factory=dict)
    rejected: dict[str, int] = field(default_factory=dict)

    def record_extracted(self, step: str, count: int) -> None:
        self.extracted[step] = count

    def record_loaded(self, step: str, count: int) -> None:
        self.loaded[step] = count

    def record_rejected(self, step: str, count: int) -> None:
        if count:
            self.rejected[step] = count

    @property
    def duration_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def summary_lines(self) -> list[str]:
        lines = [f"Duración total: {self.duration_seconds:.1f}s"]
        for step, count in self.extracted.items():
            lines.append(f"Registros extraídos [{step}]: {count}")
        for step, count in self.loaded.items():
            lines.append(f"Registros cargados [{step}]: {count}")
        for step, count in self.rejected.items():
            lines.append(f"Registros rechazados [{step}]: {count}")
        return lines
