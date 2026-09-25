"""Periodo de carga de bronze/silver/gold: [inicio, fin) en UTC, sobre
'FechaHora_UTC_Texto'. Viene de FECHA_INICIO/FECHA_FIN en '.env' o de
--fecha-inicio/--fecha-fin en main.py (ver config.cargar_configuracion). Si
ambas vienen vacias, se calcula solo (ver periodo_automatico)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from comun.exceptions import PeriodoError

# Desfase fijo de la hora local Peru/Bogota (sin horario de verano) respecto
# de UTC. Se usa para FECHA_CARGA / el log de ejecuciones, y en gold como
# respaldo si 'FechaHora' (ya local) viniera vacia.
DESFASE_HORAS_LOCAL = -5

# Hasta este dia del mes (inclusive) el periodo automatico incluye tambien el
# mes anterior, para recoger los registros tardios del mes que se esta cerrando.
DIAS_CIERRE_MES_ANTERIOR = 7


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


def _inicio_mes(anio: int, mes: int) -> datetime:
    """00:00 del dia 1 del mes; 'mes' puede salirse de 1..12 (0 = diciembre
    del anio anterior, 13 = enero del siguiente)."""
    anio, mes = anio + (mes - 1) // 12, (mes - 1) % 12 + 1
    return datetime(anio, mes, 1)


def periodo_automatico(hoy: date) -> tuple[datetime, datetime]:
    """Mes en curso completo; los primeros DIAS_CIERRE_MES_ANTERIOR dias del
    mes, tambien el mes anterior. Ej.: 2026-09-07 -> [2026-08-01, 2026-10-01);
    2026-09-08 -> [2026-09-01, 2026-10-01). Un solo rango continuo, asi
    bronze/silver/gold lo tratan igual que un periodo manual."""
    meses_atras = 1 if hoy.day <= DIAS_CIERRE_MES_ANTERIOR else 0
    return _inicio_mes(hoy.year, hoy.month - meses_atras), _inicio_mes(hoy.year, hoy.month + 1)


def resolver_periodo(
    fecha_inicio: str | None, fecha_fin: str | None, hoy: date | None = None
) -> tuple[datetime, datetime]:
    """Valida e interpreta el periodo completo. Levanta PeriodoError con un
    mensaje apto para mostrar al usuario.

    Sin FECHA_INICIO ni FECHA_FIN: periodo_automatico() sobre 'hoy' (por
    defecto, la fecha local Peru/Bogota). Solo una de las dos es un error."""
    if not fecha_inicio and not fecha_fin:
        return periodo_automatico(hoy or ahora_local().date())
    if not fecha_inicio or not fecha_fin:
        raise PeriodoError(
            "Periodo incompleto: define FECHA_INICIO y FECHA_FIN (o --fecha-inicio/--fecha-fin), "
            "o deja ambas vacias para el periodo automatico."
        )
    try:
        inicio = parse_fecha_utc(fecha_inicio)
        fin = parse_fecha_utc(fecha_fin, es_fin=True)
    except ValueError as exc:
        raise PeriodoError(f"Fecha invalida en el periodo: {exc}") from exc
    if fin <= inicio:
        raise PeriodoError("La fecha de fin debe ser posterior a la de inicio.")
    return inicio, fin
