"""Consolida 'Registro'/'Bandejas' de todos los .xlsx en '14 CORREOS'
(sitio SharePoint 'ReportingFractalia') y los carga en SQL Server
('CL_MOVIL', 172.17.0.162):

- TBL_CORREO_REGISTRO: carga por PERIODO -- elimina solo las filas cuyo
  'FechaHora_UTC_Texto' cae en [--fecha-inicio, --fecha-fin) y vuelve a
  insertar unicamente los registros consolidados de ese mismo periodo. No
  afecta filas de otros periodos ya cargados.
- TBL_CORREO_BANDEJAS: siempre reemplazo COMPLETO (TRUNCATE + INSERT de
  todo lo consolidado), sin filtro de fecha -- no tiene un campo de control
  de periodo (ver README).

Uso (desde cualquier directorio):
    python src/correos/cargar_correos.py --fecha-inicio 2026-09-01T00:00:00 --fecha-fin 2026-09-22T00:00:00

El periodo tambien se puede fijar en '.env' (FECHA_INICIO/FECHA_FIN), para
correrlo sin argumentos (p.ej. en un schedule automatizado) -- los
argumentos de linea de comandos, si se pasan, tienen prioridad sobre '.env'.

El rango es UTC, mismo huso que 'FechaHora_UTC_Texto'. El inicio es
inclusivo, el fin es exclusivo -- salvo que se de solo la fecha
(ej. --fecha-fin 2026-09-30), que cuenta como dia completo incluido.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd

_MODULE_DIR = Path(__file__).resolve().parent  # src/correos: para los imports de abajo
PROJECT_ROOT = _MODULE_DIR.parent.parent  # 11_correos/: para '.env' y 'logs/'
sys.path.insert(0, str(_MODULE_DIR))

from config import DbSettings, Settings, SharePointDestinoSettings, cargar_configuracion, cargar_configuracion_db
from consolidar import consolidar, preparar_bandejas, preparar_registro
from db import DatabaseGateway, crear_conexion
from exceptions import CorreosError
from logging_setup import NOMBRE_LOGGER, configurar_logging
from mappings import COLUMNA_CONTROL_FECHA, ESQUEMA, TABLA_BANDEJAS, TABLA_REGISTRO
from sharepoint_auth import get_graph_token
from sharepoint_client import SharePointClient

logger = logging.getLogger(NOMBRE_LOGGER)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolida Registro/Bandejas de '14 CORREOS' y los carga en CL_MOVIL"
    )
    parser.add_argument(
        "--fecha-inicio",
        default=None,
        help="UTC ISO-8601, ej. 2026-09-01T00:00:00 (inclusivo, sobre FechaHora_UTC_Texto). "
        "Si se omite, se usa FECHA_INICIO de '.env'.",
    )
    parser.add_argument(
        "--fecha-fin",
        default=None,
        help="UTC ISO-8601, ej. 2026-09-22T00:00:00 (exclusivo, sobre FechaHora_UTC_Texto), "
        "o solo fecha, ej. 2026-09-30 (ese dia incluido completo). "
        "Si se omite, se usa FECHA_FIN de '.env'.",
    )
    return parser.parse_args()


def _parse_fecha_utc(valor: str, es_fin: bool = False) -> datetime:
    """Acepta con o sin offset de zona horaria; siempre devuelve un datetime
    naive en UTC (mismo formato que preparar_registro() deja en
    'FechaHora_UTC_Texto'), para poder compararlos directamente.

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


def descargar_archivos(destino: SharePointDestinoSettings) -> dict[str, bytes]:
    """Descarga todos los .xlsx de '14 CORREOS'. Un archivo que no se puede
    descargar se omite (se registra el motivo), no detiene al resto."""
    token = get_graph_token(destino.tenant_id, destino.client_id, destino.client_secret, destino.timeout_ms)
    cliente = SharePointClient(token, destino.timeout_ms)
    site_id = cliente.resolve_site(destino.hostname, destino.site_path)
    drive_id = cliente.resolve_drive(site_id, destino.drive_name)
    nombres = cliente.list_excel_files(drive_id, destino.folder_path)
    logger.info("%s archivo(s) Excel encontrados en '%s'.", len(nombres), destino.folder_path)

    archivos: dict[str, bytes] = {}
    for nombre in nombres:
        try:
            archivos[nombre] = cliente.download_file(drive_id, f"{destino.folder_path}/{nombre}")
        except CorreosError as exc:
            logger.error("No se pudo descargar '%s', se omite: %s", nombre, exc)
    return archivos


def cargar(
    gateway: DatabaseGateway,
    registro_df: pd.DataFrame,
    bandejas_df: pd.DataFrame,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> tuple[int, int, int]:
    """Ejecuta la carga en SQL Server. 'registro_df' ya debe venir con
    'FechaHora_UTC_Texto'/'FechaHora' convertidos a datetime (ver
    consolidar.preparar_registro) y SIN filtrar por periodo -- el filtro se
    aplica aqui, para que el DELETE y el INSERT usen exactamente el mismo
    rango. Devuelve (filas_eliminadas, filas_insertadas_registro,
    filas_insertadas_bandejas)."""
    en_rango = (registro_df[COLUMNA_CONTROL_FECHA] >= fecha_inicio) & (registro_df[COLUMNA_CONTROL_FECHA] < fecha_fin)
    registro_periodo = registro_df[en_rango]
    logger.info(
        "%s de %s fila(s) de 'Registro' caen en el periodo [%s, %s).",
        len(registro_periodo),
        len(registro_df),
        fecha_inicio,
        fecha_fin,
    )

    filas_eliminadas = gateway.execute_script_rowcount(
        f"DELETE FROM [{ESQUEMA}].[{TABLA_REGISTRO}] WHERE [{COLUMNA_CONTROL_FECHA}] >= ? AND [{COLUMNA_CONTROL_FECHA}] < ?",
        (fecha_inicio, fecha_fin),
    )
    logger.info("%s fila(s) eliminadas de [%s].[%s] para el periodo.", filas_eliminadas, ESQUEMA, TABLA_REGISTRO)

    filas_insertadas_registro = gateway.bulk_insert(TABLA_REGISTRO, registro_periodo, schema=ESQUEMA)

    gateway.truncate_table(TABLA_BANDEJAS, schema=ESQUEMA)
    filas_insertadas_bandejas = gateway.bulk_insert(TABLA_BANDEJAS, bandejas_df, schema=ESQUEMA)

    return filas_eliminadas, filas_insertadas_registro, filas_insertadas_bandejas


def ejecutar(
    settings: Settings, db_settings: DbSettings, fecha_inicio: datetime, fecha_fin: datetime
) -> tuple[int, int, int]:
    """Descarga los .xlsx de '14 CORREOS', consolida, convierte tipos y
    carga a SQL Server. Devuelve (filas_eliminadas, filas_insertadas_registro,
    filas_insertadas_bandejas). Levanta CorreosError ante cualquier fallo de
    SharePoint o SQL Server -- quien llama decide si aborta o no (ver
    main.py, que la reutiliza tras la copia SharePoint -> SharePoint)."""
    archivos = descargar_archivos(settings.destino)
    registro_df, bandejas_df = consolidar(archivos)
    registro_df = preparar_registro(registro_df)
    bandejas_df = preparar_bandejas(bandejas_df)

    conn = crear_conexion(db_settings)
    try:
        gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
        return cargar(gateway, registro_df, bandejas_df, fecha_inicio, fecha_fin)
    finally:
        conn.close()


def main() -> int:
    args = parse_args()
    settings = cargar_configuracion(PROJECT_ROOT, fecha_inicio=args.fecha_inicio, fecha_fin=args.fecha_fin)
    db_settings = cargar_configuracion_db(PROJECT_ROOT)
    configurar_logging(settings.log_dir)

    if not settings.fecha_inicio or not settings.fecha_fin:
        print(
            "Debes definir el periodo: --fecha-inicio/--fecha-fin, o FECHA_INICIO/FECHA_FIN en '.env'.",
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
        eliminadas, insertadas_registro, insertadas_bandejas = ejecutar(settings, db_settings, fecha_inicio, fecha_fin)
    except CorreosError as exc:
        logger.error("Fallo la carga: %s", exc)
        return 1

    logger.info(
        "Carga finalizada. Registro: %s eliminadas / %s insertadas (periodo). Bandejas: %s insertadas (total).",
        eliminadas,
        insertadas_registro,
        insertadas_bandejas,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
