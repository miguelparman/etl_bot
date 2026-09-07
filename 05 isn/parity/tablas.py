"""
Registro de tablas destino que se pueden "fotografiar" y comparar entre una
corrida del .dtsx original y una corrida de este pipeline (ver snapshot.py /
compare.py y la sección de paridad del README).
"""
from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class TablaParidad:
    database: str
    consulta: str  # SELECT completo; se le puede agregar un WHERE extra por CLI
    claves: list[str]  # columnas que identifican una fila de forma única
    tolerancias: dict[str, float] | None = None  # columnas numéricas con tolerancia de redondeo


TABLAS: dict[str, TablaParidad] = {
    "contactos": TablaParidad(
        database=settings.db_database_analisis,
        consulta="SELECT * FROM [dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE]",
        claves=["ID CONTACTO"],
    ),
    "contactos_numeros": TablaParidad(
        database=settings.db_database_analisis,
        consulta="SELECT * FROM [dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS]",
        claves=["telefono"],
    ),
    "isn": TablaParidad(
        database=settings.db_database_isn,
        consulta="SELECT * FROM [dbo].[TBL_ISN]",
        claves=["RUT_CLIENTE"],
    ),
    "isn_calidad": TablaParidad(
        database=settings.db_database_isn,
        consulta="SELECT * FROM [dbo].[TBL_ISN_CALIDAD]",
        claves=["RUT_CLIENTE"],
    ),
    "envios_consolidado": TablaParidad(
        database=settings.db_database_calidad,
        # TBL_ISN_ENVIOS_CONSOLIDADO acumula histórico; para comparar una
        # corrida puntual hay que acotar por fecha de carga (--where).
        consulta="SELECT * FROM [dbo].[TBL_ISN_ENVIOS_CONSOLIDADO]",
        claves=["RUT_CLIENTE", "Número del caso"],
    ),
}
