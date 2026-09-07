"""Punto de entrada del ETL. Replica el DAG del paquete SSIS_CL_ISN.dtsx:

Contenedor de secuencias (4 pasos en paralelo)
    -> SECUENCIA NUEVA (SF -> historico SF -> TBL_ISN_PRE -> historico PRE, secuencial)
        -> TBL_ISN            (rama paralela A: export CSV + archivo)
        -> TBL_ISN_CALIDAD    (rama paralela B: carga de calidad)

Comportamiento ante errores: igual que SSIS sin Event Handlers configurados,
cualquier excepcion aborta todo el proceso (fail-fast) y el programa termina
con codigo de salida 1.

Se ejecuta desde la raiz del proyecto: `python main.py [--fecha-inicio ... --fecha-fin ...]`.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

from src.config.settings import Settings, default_fecha_range, load_settings
from src.database.connection import build_engine
from src.logging_setup.logger import configure_logging
from src.pipeline import aux_tables, calidad, export_csv, pre_stage, sf_stage
from src.utils.audit import RunAudit


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL SSIS_CL_ISN (migrado a Python)")
    parser.add_argument(
        "--fecha-inicio",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),  # noqa: DTZ007 - solo fecha, sin hora/zona
        default=None,
        help="Fecha de inicio del rango a procesar (YYYY-MM-DD). Default: ayer.",
    )
    parser.add_argument(
        "--fecha-fin",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),  # noqa: DTZ007 - solo fecha, sin hora/zona
        default=None,
        help="Fecha de fin del rango a procesar (YYYY-MM-DD). Default: ayer.",
    )
    return parser.parse_args(argv)


def resolve_fecha_range(
    args: argparse.Namespace, settings: Settings
) -> tuple[date, date]:
    if args.fecha_inicio and args.fecha_fin:
        return args.fecha_inicio, args.fecha_fin
    if settings.fecha_inicio and settings.fecha_fin:
        return settings.fecha_inicio, settings.fecha_fin
    return default_fecha_range()


def run_parallel_group(steps: dict[str, callable]) -> None:
    """Ejecuta funciones sin argumentos en paralelo y relanza la primera
    excepcion encontrada (equivalente a un contenedor SSIS sin restricciones
    de precedencia entre sus hijos)."""
    with ThreadPoolExecutor(max_workers=len(steps)) as executor:
        futures = {executor.submit(fn): name for name, fn in steps.items()}
        errors = []
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - se relanza mas abajo con contexto
                errors.append((name, exc))
        if errors:
            names = ", ".join(name for name, _ in errors)
            raise RuntimeError(f"Fallo en paso(s) paralelo(s): {names}") from errors[0][1]


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = load_settings()
    logger = configure_logging(settings.log_dir, settings.log_level)
    audit = RunAudit()

    fecha_inicio, fecha_fin = resolve_fecha_range(args, settings)
    logger.info("ETL iniciado (rango %s..%s)", fecha_inicio, fecha_fin)

    engine = build_engine(settings.db)
    try:
        # --- Contenedor de secuencias (paralelo) ---
        run_parallel_group(
            {
                "delete_envios_consolidado_hoy": lambda: aux_tables.delete_envios_consolidado_hoy(engine),
                "rebuild_reference_tables": lambda: aux_tables.rebuild_reference_tables(engine),
                "load_aux_contacto": lambda: aux_tables.load_aux_contacto(
                    engine, settings.db, settings.paths, audit
                ),
                "load_aux_cliente": lambda: aux_tables.load_aux_cliente(
                    engine, settings.db, settings.paths, audit
                ),
            }
        )

        # --- SECUENCIA NUEVA (secuencial) ---
        sf_stage.build_tbl_isn_sf(engine, fecha_inicio, fecha_fin)
        sf_stage.consolidate_sf_history(engine)
        pre_stage.build_tbl_isn_pre(engine)
        pre_stage.consolidate_pre_history(engine)

        # --- TBL_ISN (rama A) y TBL_ISN_CALIDAD (rama B), en paralelo ---
        run_date = date.today()  # noqa: DTZ011 - fecha local del servidor, igual que GETDATE() en el original

        def rama_export() -> None:
            export_csv.build_tbl_isn(engine)
            export_csv.export_csv(engine, settings.paths, audit)
            export_csv.archive_csv(settings.paths, run_date)

        def rama_calidad() -> None:
            calidad.build_tbl_isn_calidad(engine)
            calidad.load_envios_consolidado(engine, settings.db, audit)

        run_parallel_group({"export": rama_export, "calidad": rama_calidad})

        for line in audit.summary_lines():
            logger.info(line)
        logger.info("ETL finalizado correctamente")
        return 0

    except Exception:
        logger.exception("ETL finalizado con errores")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
