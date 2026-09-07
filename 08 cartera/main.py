"""Migracion a Python del paquete SSIS 'CL_Proc_Carga_Cartera.dtsx': carga de
la cartera de clientes vigente (Chile) desde un Excel mantenido manualmente
hacia SQL Server, con reclasificacion de estado (NUEVO/SE MANTIENE/REINGRESO)
contra el historico.

Flujo (equivalente a los 3 Sequence Containers del .dtsx -- ver
app/application/pipeline.py para el detalle completo):

    CARGA CARTERA TEMPORAL -> CARGA CARTERA ACTUAL -> HISTORICO CARTERA

Arquitectura (Clean/Layered):
    app/domain/          Entidades (Periodo, ResultadoPipeline) y excepciones.
                          Sin dependencias externas.
    app/application/     Puertos (interfaces), y los 4 pasos del proceso
                          separados por responsabilidad -- extraction.py,
                          validation.py, transformation.py, load.py -- mas
                          pipeline.py, que los orquesta en el mismo orden que
                          el Control Flow original.
    app/infrastructure/  Implementaciones concretas: Excel (pandas), SQL
                          Server (pyodbc), .env, logging.
    main.py (este archivo) Composition root: arma las piezas concretas de
                          infrastructure/ y las inyecta en CarteraPipeline.
                          Es el unico punto que conoce ambas capas a la vez.

Configuracion:
    Los valores se leen del archivo '.env' (junto a este script; ver
    '.env.example' para la lista completa). Ninguna credencial esta
    embebida en el codigo -- las 2 conexiones OLE DB del paquete original
    tenian password DPAPI-encriptado por usuario/maquina, imposible de
    reutilizar fuera de esa maquina; aqui se declaran en '.env' (no
    versionado).

Uso:
    python main.py --fecha-inicio 20260827   # equivalente a editar a mano
                                              # User::Fecha_Inicio en el .dtsx
    python main.py                           # usa VAR_FECHA_INICIO de .env
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # permite 'import app.xxx' al correr como script suelto

from app.application.pipeline import CarteraPipeline
from app.domain.exceptions import CarteraError, PipelineError, ValidacionError
from app.domain.models import Periodo, hoy_yyyymmdd
from app.infrastructure.config import cargar_configuracion
from app.infrastructure.db import crear_conexion
from app.infrastructure.logging_setup import NOMBRE_LOGGER, configurar_logging
from app.infrastructure.spreadsheet_reader import PandasExcelReader
from app.infrastructure.sqlserver_gateway import SqlServerGateway

logger = logging.getLogger(NOMBRE_LOGGER)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--fecha-inicio",
        type=int,
        default=None,
        help="Inicio del periodo de cartera vigente, formato YYYYMMDD "
        "(equivalente a User::Fecha_Inicio). Por defecto: VAR_FECHA_INICIO de .env.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = cargar_configuracion(BASE_DIR, fecha_inicio=args.fecha_inicio)
    configurar_logging(settings.log_file)

    if settings.fecha_inicio is None:
        logger.error(
            "No hay fecha de inicio de periodo disponible: defina VAR_FECHA_INICIO "
            "en .env (equivalente a User::Fecha_Inicio) o pase --fecha-inicio YYYYMMDD."
        )
        return 1

    periodo = Periodo(fecha_inicio=settings.fecha_inicio, fecha_fin=hoy_yyyymmdd())
    logger.info("Iniciando carga de Cartera para el periodo %s.", periodo)

    conn_cartera = None
    conn_temporales = None
    try:
        conn_cartera = crear_conexion(settings.db_cartera)
        conn_temporales = crear_conexion(settings.db_temporales)

        pipeline = CarteraPipeline(
            db_cartera=SqlServerGateway(conn_cartera, settings.batch_size),
            db_temporales=SqlServerGateway(conn_temporales, settings.batch_size),
            spreadsheet_reader=PandasExcelReader(),
            excel_path=settings.excel_path,
        )
        resultado = pipeline.run(periodo)

        logger.info(
            "Proceso finalizado correctamente: %s filas extraidas, %s en staging, "
            "%s copiadas a TBL_CARTERA_ACTUAL.",
            resultado.filas_extraidas,
            resultado.filas_staging,
            resultado.filas_actual,
        )
        return 0

    except PipelineError as exc:
        if isinstance(exc.causa, ValidacionError):
            logger.error("Validacion de calidad de datos fallida: %s", exc.causa)
        else:
            logger.error("Error durante la carga de Cartera: %s", exc)
        logger.exception("Detalle del error:")
        return 1

    except CarteraError as exc:
        logger.error("Error de configuracion: %s", exc)
        return 1

    finally:
        if conn_temporales is not None:
            conn_temporales.close()
        if conn_cartera is not None:
            conn_cartera.close()


if __name__ == "__main__":
    sys.exit(main())
