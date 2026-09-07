"""
Saca una "foto" del resultado actual de una tabla destino (ver
parity/tablas.py) y la guarda en disco. Se usa dos veces por tabla:

  1) Después de correr el paquete .dtsx original      -> --etiqueta ssis
  2) Después de correr el pipeline Python (este repo)  -> --etiqueta python

Uso:
    python -m parity.snapshot --tabla contactos --etiqueta ssis
    python -m parity.snapshot --tabla contactos --etiqueta python
    python -m parity.snapshot --tabla envios_consolidado --etiqueta ssis \
        --where "[FECHA DE CARGA] = '2026-09-06'"
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from db import get_engine
from parity.tablas import TABLAS

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = "parity/snapshots"


def snapshot(tabla: str, etiqueta: str, where: str | None = None) -> str:
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    definicion = TABLAS[tabla]

    sql = definicion.consulta
    if where:
        sql = f"{sql} WHERE {where}"

    engine = get_engine(definicion.database)
    df = pd.read_sql(sql, engine)

    out_path = os.path.join(SNAPSHOT_DIR, f"{tabla}_{etiqueta}.parquet")
    df.to_parquet(out_path, index=False)
    logger.info("Snapshot guardado: %s (%d filas, %d columnas)", out_path, len(df), len(df.columns))
    print(f"OK: {len(df)} filas guardadas en {out_path}")
    return out_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
    parser = argparse.ArgumentParser(description="Guarda una foto de una tabla destino para comparar paridad")
    parser.add_argument("--tabla", choices=sorted(TABLAS), required=True)
    parser.add_argument("--etiqueta", type=str, required=True, help="Ej. 'ssis' o 'python'")
    parser.add_argument("--where", type=str, default=None, help="Filtro SQL extra, ej. la fecha de carga evaluada")
    args = parser.parse_args()

    snapshot(args.tabla, args.etiqueta, args.where)
    return 0


if __name__ == "__main__":
    sys.exit(main())
