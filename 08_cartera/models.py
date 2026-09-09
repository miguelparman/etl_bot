"""Value objects del proceso de Cartera, sin dependencias externas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


_FORMATO_YYYYMMDD = re.compile(r"^\d{8}$")


def _validar_yyyymmdd(nombre: str, valor: int) -> None:
    if not _FORMATO_YYYYMMDD.match(str(valor)):
        raise ValueError(f"{nombre} debe tener formato YYYYMMDD (8 digitos): {valor}")


@dataclass(frozen=True)
class Periodo:
    """Ventana de vigencia de la carga, como enteros YYYYMMDD.

    Equivalente a las variables de paquete 'User::Fecha_Inicio' y
    'User::Fecha_Fin' de CL_Proc_Carga_Cartera.dtsx.

    'fecha_inicio' era, en el .dtsx original, un valor literal fijo escrito a
    mano en la expresion de la variable (no una formula) -- se editaba antes
    de cada corrida para marcar el inicio del periodo de cartera vigente. Aqui
    se recibe como parametro explicito (CLI/.env), nunca se calcula solo.

    'fecha_fin' si era dinamico en el paquete original (formula
    'year(...)*10000+month(...)*100+day(...)' sobre GETDATE()): la fecha de
    hoy como entero YYYYMMDD. Ver 'hoy_yyyymmdd()' mas abajo.
    """

    fecha_inicio: int
    fecha_fin: int

    def __post_init__(self) -> None:
        _validar_yyyymmdd("fecha_inicio", self.fecha_inicio)
        _validar_yyyymmdd("fecha_fin", self.fecha_fin)


def hoy_yyyymmdd(hoy: date | None = None) -> int:
    """Replica la expresion original de 'User::Fecha_Fin':
    year(dateadd("year",0,getdate()))*10000+month(...)*100+day(...).
    """
    hoy = hoy or date.today()
    return hoy.year * 10000 + hoy.month * 100 + hoy.day


@dataclass(frozen=True)
class ResultadoPipeline:
    """Resumen de una ejecucion exitosa, para logging/reporting y para los
    tests que demuestran equivalencia con el proceso SSIS original."""

    periodo: Periodo
    filas_extraidas: int
    filas_staging: int
    filas_actual: int
    filas_historico_insertadas: int
