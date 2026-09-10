"""Transformacion: tareas Execute SQL que enriquecen/reclasifican la cartera
en SQL Server, migradas literalmente desde CL_Proc_Carga_Cartera.dtsx.

Se mantienen como scripts T-SQL (no se reimplementa el join/logica en
pandas) por fidelidad: son las mismas sentencias que corria el paquete
original contra el mismo servidor, sobre las mismas tablas -- reescribirlas
como operaciones de DataFrame arriesgaria introducir diferencias sutiles de
comportamiento (NULLs, colaciones, tipos) que no aportan nada a la
migracion.
"""

from __future__ import annotations

import logging

import sql
from db import DatabaseGateway
from exceptions import CargaError

logger = logging.getLogger("cartera")


def enriquecer_con_asesores(db_temporales: DatabaseGateway) -> None:
    """Tarea 'CARGA DNI': homologa asesor/ejecutivo (SM titular, dupla,
    triada, supervisor) desde CL_DATA.dbo.TBL_PLACES y calcula RUT_SIN_DV."""
    try:
        db_temporales.execute_script(sql.ENRIQUECER_CON_ASESORES)
        db_temporales.execute_script(sql.NORMALIZAR_SUB_SEGMENTO)
    except Exception as exc:
        raise CargaError(f"Fallo 'CARGA DNI' (enriquecer_con_asesores): {exc}") from exc
    logger.info("CARGA DNI: asesores homologados y SUB_SEGME normalizado.")


def actualizar_status_historico(db_cartera: DatabaseGateway) -> None:
    """Tarea 'ACTUALIZA STATUS TEMP CARTERA': clasifica cada RUT de la
    temporal como NUEVO / SE MANTIENE / REINGRESO comparando contra el
    historico, y marca MODIFICADO para los que se mantienen con cambios."""
    try:
        db_cartera.execute_script(sql.ACTUALIZA_STATUS_TEMP_CARTERA)
    except Exception as exc:
        raise CargaError(f"Fallo 'ACTUALIZA STATUS TEMP CARTERA': {exc}") from exc
    logger.info("ACTUALIZA STATUS TEMP CARTERA: status (NUEVO/SE MANTIENE/REINGRESO) asignado.")


def limitar_clientes_historico(db_cartera: DatabaseGateway, fecha_inicio: int) -> None:
    """Tarea 'LIMITA CLIENTES': cierra en el historico (fecha_fin = dia
    anterior a fecha_inicio) a los clientes retirados y a los modificados
    del periodo vigente. Recibe 'fecha_inicio' como parametro posicional,
    igual que el .dtsx original lo tomaba de User::Fecha_Inicio."""
    try:
        db_cartera.execute_script(sql.LIMITA_CLIENTES, params=(fecha_inicio,))
    except Exception as exc:
        raise CargaError(f"Fallo 'LIMITA CLIENTES': {exc}") from exc
    logger.info("LIMITA CLIENTES: periodo anterior cerrado para retirados/modificados.")


def limpiar_temporal(db_cartera: DatabaseGateway) -> None:
    """Tarea 'LIMPIA TEMPORAL': registra 'SE MANTIENE'/'NO' en el historico
    para los no modificados y los elimina de la temporal para que 'CARGA' no
    vuelva a insertarlos."""
    try:
        db_cartera.execute_script(sql.LIMPIA_TEMPORAL)
    except Exception as exc:
        raise CargaError(f"Fallo 'LIMPIA TEMPORAL': {exc}") from exc
    logger.info("LIMPIA TEMPORAL: no modificados depurados de la temporal.")
