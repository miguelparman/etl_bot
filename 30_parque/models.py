"""Value objects del proceso de Parque, sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnaSpec:
    """Una columna del Origen/Destino OLE DB original, con su largo maximo
    (WSTR/STR declarado en el .dtsx): cualquier valor que lo exceda aborta el
    Data Flow (errorRowDisposition/truncationRowDisposition='FailComponent'
    para TODAS las columnas en el paquete original, sin excepciones)."""

    nombre: str
    longitud_max: int


@dataclass(frozen=True)
class ParqueFlowSpec:
    """Una de las 2 ramas independientes del .dtsx original ('PQ FIJO I+II' /
    'PQ MOVIL I+II'): nombre del CSV de origen (SharePoint), tabla _ACTUAL
    destino en CL_PLANTA, especificacion de columnas, y (Fase 2) tabla y
    tarea 'DELETE' de _HISTORICO -- permite que extraccion.py, validacion.py,
    transformacion.py y carga.py sean genericos y se reutilicen para ambas
    ramas en vez de duplicar el codigo.

    'nombre_historico'/'tabla_historico'/'sql_delete_historico' corresponden
    a la sub-rama 'II' del .dtsx original (p.ej. 'PQ FIJO II'), que depende
    de que la sub-rama 'I' ('PQ FIJO I') haya terminado en exito -- ver
    pipeline.py."""

    nombre: str
    archivo_csv: str
    tabla_destino: str
    columnas: tuple[ColumnaSpec, ...]
    nombre_historico: str
    tabla_historico: str
    sql_delete_historico: str

    @property
    def nombres_columnas(self) -> tuple[str, ...]:
        return tuple(c.nombre for c in self.columnas)


@dataclass(frozen=True)
class ResultadoFlujo:
    """Resumen de la carga de la tabla _ACTUAL de una rama (Fase 1: TRUNCATE
    + Data Flow 'PQ FIJO I' / 'PQ MOVIL I')."""

    nombre: str
    filas_csv: int
    filas_periodo: int
    filas_cargadas: int


@dataclass(frozen=True)
class ResultadoHistorico:
    """Resumen de la carga de la tabla _HISTORICO de una rama (Fase 2: DELETE
    + Data Flow 'PQ FIJO II' / 'PQ MOVIL II', alimentado desde la tabla
    _ACTUAL ya cargada en la Fase 1, no desde el CSV/SharePoint de nuevo)."""

    nombre: str
    filas_purgadas: int
    filas_insertadas: int


@dataclass(frozen=True)
class ResultadoRama:
    """Resultado completo de una rama (FIJO o MOVIL): _ACTUAL (Fase 1) +
    _HISTORICO (Fase 2)."""

    actual: ResultadoFlujo
    historico: ResultadoHistorico


@dataclass(frozen=True)
class ResultadoPipeline:
    """Resumen de una ejecucion del pipeline completo, para logging/reporting
    y para los tests que demuestran equivalencia con el proceso SSIS
    original."""

    periodo: str
    fijo: ResultadoRama
    movil: ResultadoRama
