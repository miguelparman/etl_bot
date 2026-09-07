"""CLI de entrada. Reemplaza a la ejecucion manual/programada de los paquetes
.dtsx via dtexec/SSMS/SQL Server Agent.

El pipeline de Ventas necesita una fecha de corte, equivalente a la Package
Variable `User::Fecha` del .dtsx original (ver PackageParameters en
config/settings.py). Por defecto se toma de VAR_FECHA en `.env`; `--fecha`
es opcional y, si se pasa, la sobreescribe puntualmente para esa ejecucion.

Si se ejecuta SIN ningun subcomando (p.ej. con el boton "Run Python File" de
VS Code, que corre `python main.py` sin argumentos) se asume "all": corre el
procedimiento completo, Señalizaciones y luego Ventas, en ese orden -- igual
que ejecutar ambos paquetes .dtsx originales uno despues del otro.

Uso:
    python main.py                          # equivale a "all"
    python main.py senalizaciones
    python main.py ventas
    python main.py ventas --fecha 2026-08-01
    python main.py all
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

from etl_chile.domain.exceptions import EtlChileError
from etl_chile.infrastructure.logging_config import configure_logging
from etl_chile.presentation.container import Container


def _parse_fecha(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Fecha invalida '{value}', formato esperado YYYY-MM-DD"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etl-chile",
        description="Migracion Python de CROSS 0101 SSIS_CL_Senalizaciones.dtsx "
        "y CROSS 0102 SSIS_CL_Ventas.dtsx",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser(
        "senalizaciones", help="Ejecuta el pipeline de Señalizaciones (CROSS 0101)"
    )

    ventas_parser = subparsers.add_parser(
        "ventas", help="Ejecuta el pipeline de Ventas (CROSS 0102)"
    )
    ventas_parser.add_argument(
        "--fecha",
        required=False,
        type=_parse_fecha,
        default=None,
        help="Fecha de corte (equivalente a la variable User::Fecha, "
        "declarada como VAR_FECHA en .env). Si se pasa, sobreescribe "
        "puntualmente el valor de .env para esta ejecucion. Formato YYYY-MM-DD",
    )

    all_parser = subparsers.add_parser(
        "all",
        help="Ejecuta Señalizaciones (CROSS 0101) y luego Ventas (CROSS 0102), en ese orden",
    )
    all_parser.add_argument(
        "--fecha",
        required=False,
        type=_parse_fecha,
        default=None,
        help="Fecha de corte para el pipeline de Ventas (ver VAR_FECHA en .env). "
        "Formato YYYY-MM-DD",
    )

    return parser


def _resolve_fecha(fecha_arg: date | None, container: Container) -> date:
    fecha = fecha_arg or container.settings.parameters.fecha
    if fecha is None:
        raise EtlChileError(
            "No hay fecha de corte disponible: defina VAR_FECHA en .env "
            "(equivalente a la variable User::Fecha del .dtsx original) o "
            "pase --fecha YYYY-MM-DD."
        )
    return fecha


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Sin subcomando (p.ej. boton "Run Python File" de VS Code, que ejecuta
    # `python main.py` sin argumentos) se corre el procedimiento completo.
    command = args.command or "all"
    fecha_arg = getattr(args, "fecha", None)

    try:
        container = Container.build()
        configure_logging(container.settings.log_level)

        # El orden de "all" respeta al del proyecto SSIS original: primero
        # CROSS 0101 SSIS_CL_Senalizaciones.dtsx, despues CROSS 0102
        # SSIS_CL_Ventas.dtsx.
        if command == "senalizaciones":
            container.senalizaciones_pipeline.run()
        elif command == "ventas":
            container.ventas_pipeline.run(_resolve_fecha(fecha_arg, container))
        elif command == "all":
            container.senalizaciones_pipeline.run()
            container.ventas_pipeline.run(_resolve_fecha(fecha_arg, container))
    except EtlChileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0
