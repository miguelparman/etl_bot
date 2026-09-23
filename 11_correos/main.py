"""Punto de entrada del proceso completo:

1. Copia todos los Excel de 'Control Correos Chile' (sitio SharePoint 'BPO')
   hacia '14 CORREOS' (sitio SharePoint 'ReportingFractalia').
2. Consolida 'Registro'/'Bandejas' de esos archivos y los carga en SQL
   Server ('CL_MOVIL') -- ver cargar_correos.py. El periodo de carga de
   TBL_CORREO_REGISTRO se toma de FECHA_INICIO/FECHA_FIN en '.env'. Es la
   capa BRONZE.
3. Construye la capa SILVER (TBL_CORREO_REGISTRO_SILVER) del mismo periodo
   leyendo bronze y agregando ASUNTO_AGRUPADO -- ver silver.py.
4. Construye la capa GOLD (modelo estrella en el esquema 'gold') del mismo
   periodo desde silver, y valida que cuadre -- ver gold.py.

Un fallo en un paso no deshace los anteriores (los archivos ya copiados a
SharePoint quedan ahi, bronze/silver quedan cargados) -- son operaciones
independientes, cada una reintentable por su cuenta (main.py de nuevo, o
cargar_correos.py / cargar_silver.py / cargar_gold.py solos).

Uso:
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # 11_correos/: para '.env' y 'logs/'
sys.path.insert(0, str(BASE_DIR / "src" / "correos"))

from cargar_correos import _parse_fecha_utc, ejecutar
from config import cargar_configuracion, cargar_configuracion_db
from copiar_correos import copiar_correos
from db import DatabaseGateway, crear_conexion
from exceptions import CorreosError
from gold import cargar_periodo_gold, validar
from logging_setup import configurar_logging
from sharepoint_auth import get_graph_token
from sharepoint_client import SharePointClient
from silver import cargar_periodo_silver


def main() -> int:
    settings = cargar_configuracion(BASE_DIR)
    logger = configurar_logging(settings.log_dir)

    try:
        destino = settings.destino
        token_destino = get_graph_token(destino.tenant_id, destino.client_id, destino.client_secret, destino.timeout_ms)
        cliente_destino = SharePointClient(token_destino, destino.timeout_ms)
        site_id_destino = cliente_destino.resolve_site(destino.hostname, destino.site_path)
        drive_id_destino = cliente_destino.resolve_drive(site_id_destino, destino.drive_name)
        folder_id_destino = cliente_destino.resolve_folder(drive_id_destino, destino.folder_path)

        resultados = copiar_correos(settings.origen, cliente_destino, drive_id_destino, folder_id_destino)
    except CorreosError as exc:
        logger.error("No se pudo completar la copia: %s", exc)
        return 1

    exitosos = [r for r in resultados if r.ok]
    fallidos_copia = [r for r in resultados if not r.ok]
    logger.info(
        "Copia finalizada: %s exitoso(s), %s fallido(s) de %s archivo(s).",
        len(exitosos),
        len(fallidos_copia),
        len(resultados),
    )
    for r in fallidos_copia:
        logger.error("  - %s: %s", r.nombre, r.error)

    if not settings.fecha_inicio or not settings.fecha_fin:
        logger.error(
            "FECHA_INICIO/FECHA_FIN no estan definidas en '.env': no se puede cargar TBL_CORREO_REGISTRO/"
            "TBL_CORREO_BANDEJAS."
        )
        return 1
    try:
        fecha_inicio = _parse_fecha_utc(settings.fecha_inicio)
        fecha_fin = _parse_fecha_utc(settings.fecha_fin, es_fin=True)
    except ValueError as exc:
        logger.error("FECHA_INICIO/FECHA_FIN invalida en '.env': %s", exc)
        return 1
    if fecha_fin <= fecha_inicio:
        logger.error("FECHA_FIN debe ser posterior a FECHA_INICIO.")
        return 1

    db_settings = cargar_configuracion_db(BASE_DIR)
    try:
        eliminadas, insertadas_registro, insertadas_bandejas = ejecutar(settings, db_settings, fecha_inicio, fecha_fin)
    except CorreosError as exc:
        logger.error("Fallo la carga a SQL Server: %s", exc)
        return 1

    logger.info(
        "Carga finalizada. Registro: %s eliminadas / %s insertadas (periodo). Bandejas: %s insertadas (total).",
        eliminadas,
        insertadas_registro,
        insertadas_bandejas,
    )

    try:
        conn = crear_conexion(db_settings)
        try:
            gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
            eliminadas_silver, insertadas_silver = cargar_periodo_silver(gateway, fecha_inicio, fecha_fin)
        finally:
            conn.close()
    except CorreosError as exc:
        logger.error("Fallo la carga de silver (bronze ya quedo cargado): %s", exc)
        return 1

    logger.info("Silver finalizada: %s eliminadas / %s insertadas (periodo).", eliminadas_silver, insertadas_silver)

    try:
        conn = crear_conexion(db_settings)
        try:
            gateway = DatabaseGateway(conn, batch_size=db_settings.batch_size)
            eliminadas_gold, insertadas_gold = cargar_periodo_gold(gateway, fecha_inicio, fecha_fin)
            gold_ok = validar(gateway, (fecha_inicio, fecha_fin))
        finally:
            conn.close()
    except CorreosError as exc:
        logger.error("Fallo la carga de gold (bronze y silver ya quedaron cargados): %s", exc)
        return 1

    logger.info("Gold finalizada: %s eliminadas / %s insertadas en FACT_MENSAJE (periodo).", eliminadas_gold, insertadas_gold)
    return 1 if fallidos_copia or not gold_ok else 0


if __name__ == "__main__":
    sys.exit(main())
