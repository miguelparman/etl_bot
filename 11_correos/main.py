"""Punto de entrada unico del proceso (estructura medallion):

1. ingesta: copia todos los Excel de 'Control Correos Chile' (sitio
   SharePoint 'BPO') hacia '14 CORREOS' (sitio 'ReportingFractalia').
2. bronze:  consolida 'Registro'/'Bandejas' de esos archivos y los carga tal
   cual en SQL Server ('CL_MOVIL'), por periodo.
3. silver:  bronze -> TBL_CORREO_REGISTRO_SILVER (limpio + ASUNTO_AGRUPADO).
4. gold:    silver -> modelo estrella en el esquema 'gold', y valida que cuadre.

El periodo sale de FECHA_INICIO/FECHA_FIN en '.env' (o --fecha-inicio/
--fecha-fin). Un fallo en una etapa detiene las siguientes pero no deshace
las anteriores; se reintenta con --desde / --solo.

Uso:
    python main.py                            # todo: ingesta -> bronze -> silver -> gold
    python main.py --desde silver             # reintentar desde silver (bronze ya cargado)
    python main.py --solo gold                # una sola etapa
    python main.py --solo gold --completo     # reconstruir una etapa completa (silver/gold)
    python main.py --fecha-inicio 2026-09-01 --fecha-fin 2026-09-30
    python main.py --verificar-copia          # solo auditar la copia de ingesta
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # 11_correos/: para '.env' y 'logs/'
sys.path.insert(0, str(BASE_DIR / "src" / "correos"))

from bronze.cargar import ejecutar_bronze
from comun.config import Settings, cargar_configuracion, cargar_configuracion_db
from comun.db import DatabaseGateway, crear_conexion
from comun.exceptions import CorreosError
from comun.logging_setup import NOMBRE_LOGGER, configurar_logging
from comun.periodo import resolver_periodo
from gold.cargar import cargar_periodo_gold, recargar_gold_completo, validar
from ingesta.copiar import ejecutar_copia
from ingesta.verificar_copia import ejecutar_verificacion
from silver.cargar import cargar_periodo_silver, recargar_silver_completo

logger = logging.getLogger(NOMBRE_LOGGER)

ETAPAS = ["ingesta", "bronze", "silver", "gold"]
# Etapas que pueden reconstruirse completas (bronze siempre es por periodo:
# reconstruir desde los .xlsx implica pasar el periodo que cubren).
ETAPAS_CON_COMPLETO = {"silver", "gold"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="11_correos: ingesta -> bronze -> silver -> gold")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--desde", choices=ETAPAS, help="Corre desde esta etapa hasta gold.")
    grupo.add_argument("--solo", choices=ETAPAS, help="Corre solo esta etapa.")
    grupo.add_argument("--verificar-copia", action="store_true", help="Solo audita la copia de ingesta.")
    parser.add_argument(
        "--completo",
        action="store_true",
        help="Silver/gold se reconstruyen completos (sin filtro de periodo). Solo con --solo/--desde silver|gold.",
    )
    parser.add_argument("--fecha-inicio", default=None, help="UTC; solo fecha (2026-09-01) o fecha y hora. Si se omite, FECHA_INICIO de '.env'.")
    parser.add_argument("--fecha-fin", default=None, help="UTC; solo fecha (2026-09-30, dia incluido completo) o fecha y hora (exclusiva). Si se omite, FECHA_FIN de '.env'.")
    args = parser.parse_args(argv)

    args.etapas = seleccionar_etapas(args.desde, args.solo)
    if args.completo and not set(args.etapas) <= ETAPAS_CON_COMPLETO:
        parser.error("--completo solo aplica a silver/gold: usa --solo silver|gold o --desde silver|gold.")
    return args


def seleccionar_etapas(desde: str | None, solo: str | None) -> list[str]:
    if solo:
        return [solo]
    return ETAPAS[ETAPAS.index(desde):] if desde else list(ETAPAS)


def _necesita_periodo(etapas: list[str], completo: bool) -> bool:
    return "bronze" in etapas or (not completo and bool(set(etapas) & ETAPAS_CON_COMPLETO))


def ejecutar_etapas_db(
    gateway: DatabaseGateway,
    settings: Settings,
    etapas: list[str],
    periodo: tuple[datetime, datetime] | None,
    completo: bool,
) -> bool:
    """bronze / silver / gold sobre una misma conexion. Devuelve False si la
    validacion de gold no cuadra."""
    if "bronze" in etapas:
        ejecutar_bronze(settings.destino, gateway, *periodo)

    if "silver" in etapas:
        if completo:
            insertadas = recargar_silver_completo(gateway)
            logger.info("Silver reconstruida completa: %s fila(s) insertadas.", insertadas)
        else:
            eliminadas, insertadas = cargar_periodo_silver(gateway, *periodo)
            logger.info("Silver finalizada: %s eliminadas / %s insertadas (periodo).", eliminadas, insertadas)

    if "gold" in etapas:
        if completo:
            insertadas = recargar_gold_completo(gateway)
            logger.info("Gold reconstruida completa: %s fila(s) en FACT_MENSAJE.", insertadas)
            return validar(gateway, None)
        eliminadas, insertadas = cargar_periodo_gold(gateway, *periodo)
        logger.info("Gold finalizada: %s eliminadas / %s insertadas en FACT_MENSAJE (periodo).", eliminadas, insertadas)
        return validar(gateway, periodo)
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = cargar_configuracion(BASE_DIR, fecha_inicio=args.fecha_inicio, fecha_fin=args.fecha_fin)
    configurar_logging(settings.log_dir)

    try:
        if args.verificar_copia:
            return 0 if ejecutar_verificacion(settings) else 1

        # El periodo se valida ANTES de empezar: no tiene sentido copiar si
        # despues bronze no va a poder cargar.
        periodo = None
        if _necesita_periodo(args.etapas, args.completo):
            periodo = resolver_periodo(settings.fecha_inicio, settings.fecha_fin)
        logger.info("Etapas: %s%s.", " -> ".join(args.etapas), " (completo)" if args.completo else f" | periodo {periodo}")

        copia_ok = True
        if "ingesta" in args.etapas:
            copia_ok = all(r.ok for r in ejecutar_copia(settings))

        etapas_db = [e for e in args.etapas if e != "ingesta"]
        gold_ok = True
        if etapas_db:
            db_settings = cargar_configuracion_db(BASE_DIR)
            conn = crear_conexion(db_settings)
            try:
                gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
                gold_ok = ejecutar_etapas_db(gateway, settings, etapas_db, periodo, args.completo)
            finally:
                conn.close()
    except CorreosError as exc:
        logger.error("Proceso detenido: %s", exc)
        return 1

    return 0 if copia_ok and gold_ok else 1


if __name__ == "__main__":
    sys.exit(main())
