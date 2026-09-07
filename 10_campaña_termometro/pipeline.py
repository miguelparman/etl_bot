"""
Orquestación del pipeline. Reemplaza el Control Flow del .dtsx:

  SOURCE (clientes)             \\
  Contenedor de secuencias       |-> convergen en -> Contenedor "162" (paso final)
  (detractores)                  |
  SALESFORCE 1 (encuestas)      /

Las tres primeras ramas corren en paralelo (igual que en SSIS, donde no
dependen entre sí), y el paso final solo arranca cuando las tres terminan
exitosamente -- igual que las Precedence Constraints originales.
"""
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from db import run_sql_file
from loaders.sql_loader import truncate_table, load_dataframe
from extractors.excel_extractor import read_excel_sheet
from extractors.csv_extractor import read_salesforce_csv
from transformers.clientes import transform_clientes
from transformers.detractores import transform_detractores
from transformers.encuestas import transform_encuestas
from config import settings

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent / "sql"


def rama_clientes(periodo: int) -> None:
    """Reemplaza el contenedor 'SOURCE': TRUNCATE + Data Flow 'BASE TERMOMETRO'."""
    logger.info("[clientes] inicio")
    truncate_table("TBL_CAMPAÑA_TERMOMETRO_SOURCE")
    df = read_excel_sheet(settings.excel_clientes_path, settings.excel_clientes_sheet)
    df = transform_clientes(df, periodo)
    load_dataframe(df, "TBL_CAMPAÑA_TERMOMETRO_SOURCE")
    logger.info("[clientes] fin (%d filas)", len(df))


def rama_detractores() -> None:
    """Reemplaza 'Contenedor de secuencias': TRUNCATE + Data Flow detractores."""
    logger.info("[detractores] inicio")
    truncate_table("TBL_CAMPAÑA_TERMOMETRO_DETRACTOR")
    df = read_excel_sheet(settings.excel_clientes_path, settings.excel_detractores_sheet)
    df = transform_detractores(df)
    load_dataframe(df, "TBL_CAMPAÑA_TERMOMETRO_DETRACTOR")
    logger.info("[detractores] fin (%d filas)", len(df))


def rama_salesforce(periodo: int, fecha_inicio: str, fecha_fin: str) -> None:
    """Reemplaza 'SALESFORCE 1': DELETE PERIODO -> carga CSV -> limpieza -> ESTADO -> PESO."""
    logger.info("[salesforce] inicio")
    run_sql_file(f"{SQL_DIR}/delete_periodo_sf.sql", {"periodo": periodo})

    df = read_salesforce_csv()
    df = transform_encuestas(df, periodo)
    load_dataframe(df, "TBL_CAMPAÑA_TERMOMETRO_SF_TEMP")

    run_sql_file(f"{SQL_DIR}/delete_fuera_rango.sql", {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin})
    run_sql_file(f"{SQL_DIR}/update_estado.sql", {"periodo": periodo})
    run_sql_file(f"{SQL_DIR}/update_peso.sql", {"periodo": periodo})
    logger.info("[salesforce] fin (%d filas)", len(df))


def paso_final(periodo: int, fecha_evaluacion: str, fecha_fin_evaluacion: str) -> None:
    """Reemplaza el contenedor '162': DELETE PERIODO EN EVALUACION + INSERT final."""
    logger.info("[final] inicio")
    run_sql_file(f"{SQL_DIR}/delete_periodo_evaluacion.sql", {"periodo": periodo})
    run_sql_file(
        f"{SQL_DIR}/insert_final.sql",
        {
            "periodo": periodo,
            "fecha_evaluacion": fecha_evaluacion,
            "fecha_fin_evaluacion": fecha_fin_evaluacion,
        },
    )
    logger.info("[final] fin")


def run(periodo: int, fecha_inicio: str, fecha_fin: str) -> None:
    ramas = {
        "clientes": lambda: rama_clientes(periodo),
        "detractores": lambda: rama_detractores(),
        "salesforce": lambda: rama_salesforce(periodo, fecha_inicio, fecha_fin),
    }

    logger.info("Ejecutando las 3 ramas en paralelo: %s", list(ramas))
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in ramas.items()}
        errores = []
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as exc:
                logger.exception("La rama '%s' falló", name)
                errores.append((name, exc))

    if errores:
        raise RuntimeError(
            f"El pipeline se detuvo: fallaron las ramas {[n for n, _ in errores]}. "
            "El paso final no se ejecuta (igual que las Precedence Constraints originales)."
        )

    paso_final(periodo, fecha_inicio, fecha_fin)
