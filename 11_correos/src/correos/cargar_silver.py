"""Construye la capa SILVER (TBL_CORREO_REGISTRO_SILVER) desde bronze
(TBL_CORREO_REGISTRO) -- ver silver.py. main.py ya lo hace despues de cargar
bronze; este script sirve para reintentar solo esta etapa, o para
reconstruir silver completa (carga inicial / tras cambiar las reglas de
ASUNTO_AGRUPADO en mappings.py).

Uso (desde cualquier directorio):
    python src/correos/cargar_silver.py                        # periodo FECHA_INICIO/FECHA_FIN de '.env'
    python src/correos/cargar_silver.py --fecha-inicio 2026-09-01 --fecha-fin 2026-09-30
    python src/correos/cargar_silver.py --completo             # TODO bronze, sin filtro de fecha
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent  # src/correos: para los imports de abajo
PROJECT_ROOT = _MODULE_DIR.parent.parent  # 11_correos/: para '.env' y 'logs/'
sys.path.insert(0, str(_MODULE_DIR))

from cargar_correos import _parse_fecha_utc
from config import cargar_configuracion, cargar_configuracion_db
from db import DatabaseGateway, crear_conexion
from exceptions import CorreosError
from logging_setup import NOMBRE_LOGGER, configurar_logging
from silver import cargar_periodo_silver, recargar_silver_completo

logger = logging.getLogger(NOMBRE_LOGGER)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye TBL_CORREO_REGISTRO_SILVER desde TBL_CORREO_REGISTRO")
    parser.add_argument("--fecha-inicio", default=None, help="Igual que en cargar_correos.py. Si se omite, FECHA_INICIO de '.env'.")
    parser.add_argument("--fecha-fin", default=None, help="Igual que en cargar_correos.py. Si se omite, FECHA_FIN de '.env'.")
    parser.add_argument(
        "--completo", action="store_true", help="Reconstruye silver completa desde todo bronze (ignora el periodo)."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = cargar_configuracion(PROJECT_ROOT, fecha_inicio=args.fecha_inicio, fecha_fin=args.fecha_fin)
    db_settings = cargar_configuracion_db(PROJECT_ROOT)
    configurar_logging(settings.log_dir)

    if not args.completo:
        if not settings.fecha_inicio or not settings.fecha_fin:
            print(
                "Debes definir el periodo (--fecha-inicio/--fecha-fin o FECHA_INICIO/FECHA_FIN en '.env'), "
                "o usar --completo.",
                file=sys.stderr,
            )
            return 1
        try:
            fecha_inicio = _parse_fecha_utc(settings.fecha_inicio)
            fecha_fin = _parse_fecha_utc(settings.fecha_fin, es_fin=True)
        except ValueError as exc:
            print(f"Fecha invalida: {exc}", file=sys.stderr)
            return 1
        if fecha_fin <= fecha_inicio:
            print("La fecha de fin debe ser posterior a la de inicio.", file=sys.stderr)
            return 1

    try:
        conn = crear_conexion(db_settings)
        try:
            gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
            if args.completo:
                insertadas = recargar_silver_completo(gateway)
                logger.info("Silver reconstruida completa: %s fila(s) insertadas.", insertadas)
            else:
                eliminadas, insertadas = cargar_periodo_silver(gateway, fecha_inicio, fecha_fin)
                logger.info("Silver: %s eliminadas / %s insertadas (periodo).", eliminadas, insertadas)
        finally:
            conn.close()
    except CorreosError as exc:
        logger.error("Fallo la carga de silver: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
