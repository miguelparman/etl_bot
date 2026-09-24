"""Periodo de carga de bronze/silver/gold: [inicio, fin) en UTC, sobre
'FechaHora_UTC_Texto'. Viene de FECHA_INICIO/FECHA_FIN en '.env' o de
--fecha-inicio/--fecha-fin en main.py (ver config.cargar_configuracion)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from comun.exceptions import PeriodoError

# Desfase fijo de la hora local Peru/Bogota (sin horario de verano) respecto
# de UTC. Se usa para FECHA_CARGA / el log de ejecuciones, y en gold como
# respaldo si 'FechaHora' (ya local) viniera vacia.
DESFASE_HORAS_LOCAL = -5


def ahora_local() -> datetime:
    """Fecha y hora actual en hora local Peru/Bogota, naive y al segundo
    (mismo criterio que FECHA_HORA_LOCAL en gold). Se calcula desde UTC con
    el desfase fijo, asi no depende de la zona horaria de la maquina que
    corre el proceso."""
    return (datetime.now(timezone.utc) + timedelta(hours=DESFASE_HORAS_LOCAL)).replace(tzinfo=None, microsecond=0)


def parse_fecha_utc(valor: str, es_fin: bool = False) -> datetime:
    """Acepta con o sin offset de zona horaria; siempre devuelve un datetime
    naive en UTC (mismo formato que bronze deja en 'FechaHora_UTC_Texto'),
    para poder compararlos directamente.

    Tambien acepta solo fecha ('2026-09-30'), como dia COMPLETO: de inicio es
    00:00 de ese dia; de fin (es_fin=True) es 00:00 del dia siguiente, para
    que con el fin exclusivo del rango el ultimo dia quede incluido entero."""
    try:
        dia = date.fromisoformat(valor)
    except ValueError:
        pass
    else:
        dt = datetime.combine(dia, time.min)
        return dt + timedelta(days=1) if es_fin else dt

    dt = datetime.fromisoformat(valor)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def resolver_periodo(fecha_inicio: str | None, fecha_fin: str | None) -> tuple[datetime, datetime]:
    """Valida e interpreta el periodo completo. Levanta PeriodoError con un
    mensaje apto para mostrar al usuario."""
    if not fecha_inicio or not fecha_fin:
        raise PeriodoError(
            "Debes definir el periodo: FECHA_INICIO/FECHA_FIN en '.env', o --fecha-inicio/--fecha-fin."
        )
    try:
        inicio = parse_fecha_utc(fecha_inicio)
        fin = parse_fecha_utc(fecha_fin, es_fin=True)
    except ValueError as exc:
        raise PeriodoError(f"Fecha invalida en el periodo: {exc}") from exc
    if fin <= inicio:
        raise PeriodoError("La fecha de fin debe ser posterior a la de inicio.")
    return inicio, fin
