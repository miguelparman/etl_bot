"""Value objects del proceso de VENTAS/SEÑALIZACIONES, sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnaSpec:
    """Una columna de un Data Flow original (componente 'Conversión de
    datos' / Data Convert), con su tipo destino y su disposicion de
    error/truncamiento:

    - tipo='texto': 'longitud_max' es el ancho WSTR/STR declarado.
      estricto=True ('FailComponent'): excede el ancho -> ValidacionError.
      estricto=False ('IgnoreFailure'): se trunca en silencio.
    - tipo='numero'/'entero'/'fecha': 'longitud_max' no aplica (queda en 0).
      estricto=True ('FailComponent'): no parsea -> ValidacionError.
      estricto=False ('IgnoreFailure'): no parsea -> NULL (coerce), sin abortar.
      'numero' emula un destino DT_R8 (float, admite decimales); 'entero'
      emula un destino DT_I4 (se redondea y castea a entero -- usar cuando
      el .dtsx original declara el output del Data Convert como DT_I4, no
      DT_R8, aunque el origen sea numerico con decimales).
    """

    nombre: str
    longitud_max: int = 0
    estricto: bool = True
    tipo: str = "texto"


@dataclass(frozen=True)
class ResultadoSubPipeline:
    """Resumen de la ejecucion de UN paquete .dtsx migrado (una de las
    funciones 'ejecutar_*' de pipeline.py), para logging/reporting y para los
    tests que demuestran equivalencia con el proceso SSIS original."""

    nombre: str
    filas_por_paso: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoPipeline:
    """Resumen de 'ejecutar_todo()': un ResultadoSubPipeline por cada uno de
    los 2 paquetes, en el orden original (0101 Señalizaciones, 0102 Ventas)."""

    resultados: tuple[ResultadoSubPipeline, ...]
