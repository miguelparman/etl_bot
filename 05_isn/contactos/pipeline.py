"""
Orquestación de SSIS_CL_ISN_Contactos.dtsx. Reproduce el Control Flow:

  TRUNCATE -> Data Flow "TBL_CONTACTOS_AUTORIZADOS_CHILE" (extract+validate+
  transform+load) -> UPDATE "_0" (limpieza teléfonos)
      -> Contenedor de secuencias: TRUNCATE -> Data Flow "Números (Local)"
         (extract+load)

NOTA de orden: a diferencia del .dtsx (donde el TRUNCATE es la primera tarea
del Control Flow), acá se extrae/valida/transforma ANTES de truncar. El
resultado final es idéntico, pero si el CSV de origen no existe o falla la
validación, la tabla de producción nunca se toca -- en vez de quedar vacía
sin poder recargarse porque el TRUNCATE ya se ejecutó y la lectura del
archivo revienta después.
"""
from __future__ import annotations

import logging

from contactos import extractor, loader, validator
from contactos.transformer import transform_contactos

logger = logging.getLogger(__name__)


def run() -> dict:
    logger.info("[contactos] inicio")

    df_crudo = extractor.leer_csv_contactos()
    validator.validar_contactos(df_crudo)
    df_transformado = transform_contactos(df_crudo)

    loader.truncar_contactos()
    filas_contactos = loader.cargar_contactos(df_transformado)

    loader.limpiar_telefonos()

    df_numeros = extractor.extraer_numeros_distintos()
    loader.truncar_numeros()
    filas_numeros = loader.cargar_numeros(df_numeros)

    logger.info("[contactos] fin (%d contactos, %d números distintos)", filas_contactos, filas_numeros)
    return {"filas_contactos": filas_contactos, "filas_numeros": filas_numeros}
