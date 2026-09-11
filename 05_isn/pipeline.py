"""
Orquestador raíz. Corre los dos paquetes migrados EN ESE ORDEN (pedido
explícito: SSIS_CL_ISN_Contactos primero, SSIS_CL_ISN después), ya que el
segundo depende de tablas que pertenecen al primero
(CL_ANALISIS.TBL_CONTACTOS_AUTORIZADOS_CHILE, consultada dentro de
'TBL_ISN_SF' vía VIEW_CONTACTOS_AUTORIZADOS_CHILE_RUC_CORREO_*).
"""
from __future__ import annotations

import logging

import contactos.pipeline as contactos_pipeline
import isn.pipeline as isn_pipeline

logger = logging.getLogger(__name__)


def run(fecha_inicio: str | None = None, fecha_fin: str | None = None, saltar: set[str] | None = None) -> None:
    saltar = saltar or set()

    if "contactos" not in saltar:
        contactos_pipeline.run()
    else:
        logger.info("[contactos] omitido (--saltar contactos)")

    if "isn" not in saltar:
        isn_pipeline.run(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    else:
        logger.info("[isn] omitido (--saltar isn)")
