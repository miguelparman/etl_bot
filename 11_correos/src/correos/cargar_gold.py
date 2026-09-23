"""Construye la capa GOLD (modelo estrella en el esquema 'gold') desde
silver -- ver gold.py. main.py ya lo hace despues de silver; este script
sirve para reintentar solo esta etapa, o para reconstruir la tabla de hechos
completa (carga inicial / tras reconstruir silver con --completo).

Uso (desde cualquier directorio):
    python src/correos/cargar_gold.py                        # periodo FECHA_INICIO/FECHA_FIN de '.env'
    python src/correos/cargar_gold.py --fecha-inicio 2026-09-01 --fecha-fin 2026-09-30
    python src/correos/cargar_gold.py --completo             # TODO silver, sin filtro de fecha
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
from gold import cargar_periodo_gold, recargar_gold_completo, validar
from logging_setup import NOMBRE_LOGGER, configurar_logging

logger = logging.getLogger(NOMBRE_LOGGER)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye el modelo estrella [gold] desde TBL_CORREO_REGISTRO_SILVER")
    parser.add_argument("--fecha-inicio", default=None, help="Igual que en cargar_correos.py. Si se omite, FECHA_INICIO de '.env'.")
    parser.add_argument("--fecha-fin", default=None, help="Igual que en cargar_correos.py. Si se omite, FECHA_FIN de '.env'.")
    parser.add_argument(
        "--completo", action="store_true", help="Reconstruye FACT_MENSAJE completa desde todo silver (ignora el periodo)."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = cargar_configuracion(PROJECT_ROOT, fecha_inicio=args.fecha_inicio, fecha_fin=args.fecha_fin)
    db_settings = cargar_configuracion_db(PROJECT_ROOT)
    configurar_logging(settings.log_dir)

    periodo = None
    if not args.completo:
        if not settings.fecha_inicio or not settings.fecha_fin:
            print(
                "Debes definir el periodo (--fecha-inicio/--fecha-fin o FECHA_INICIO/FECHA_FIN en '.env'), "
                "o usar --completo.",
                file=sys.stderr,
            )
            return 1
        try:
            periodo = (_parse_fecha_utc(settings.fecha_inicio), _parse_fecha_utc(settings.fecha_fin, es_fin=True))
        except ValueError as exc:
            print(f"Fecha invalida: {exc}", file=sys.stderr)
            return 1
        if periodo[1] <= periodo[0]:
            print("La fecha de fin debe ser posterior a la de inicio.", file=sys.stderr)
            return 1

    try:
        conn = crear_conexion(db_settings)
        try:
            gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
            if periodo is None:
                insertadas = recargar_gold_completo(gateway)
                logger.info("Gold reconstruida completa: %s fila(s) en FACT_MENSAJE.", insertadas)
            else:
                eliminadas, insertadas = cargar_periodo_gold(gateway, *periodo)
                logger.info("Gold: %s eliminadas / %s insertadas en FACT_MENSAJE (periodo).", eliminadas, insertadas)
            ok = validar(gateway, periodo)
        finally:
            conn.close()
    except CorreosError as exc:
        logger.error("Fallo la carga de gold: %s", exc)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
