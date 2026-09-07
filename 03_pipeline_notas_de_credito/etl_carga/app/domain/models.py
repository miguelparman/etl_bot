"""Modelos de dominio: value objects sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PeriodoCarga:
    """Año/mes de Notas de Crédito que se está recargando (equivalente a las
    variables User::Año / User::Mes del paquete SSIS)."""

    anio: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise ValueError(f"Mes fuera de rango (1-12): {self.mes}")


@dataclass(frozen=True)
class ColumnasNC:
    """Orden y nombres de columnas del flujo NC_TEMP -> NC (Data Flow 'CARGA NC')."""

    nombres: tuple[str, ...] = (
        "RUT",
        "RAZON_SOCIAL",
        "FOLIO_NC",
        "FECHA_NC",
        "NETO_NC",
        "IVA_NC",
        "TOTAL_NC",
        "EJECUTIVO",
    )


@dataclass(frozen=True)
class ETLSettings:
    """Configuración completa de una ejecución del ETL."""

    periodo: PeriodoCarga

    db_driver: str
    db_server: str
    db_database: str
    db_uid: str
    db_pwd: str
    db_encrypt: str
    db_trust_server_certificate: str

    excel_path: Path
    tabla_staging: str
    tabla_destino: str
    columnas: ColumnasNC = field(default_factory=ColumnasNC)
    batch_size: int = 5000

    log_file: Path = Path("etl_nc.log")


@dataclass(frozen=True)
class ResultadoETL:
    """Resumen de una ejecución exitosa, para logging/reporting."""

    periodo: PeriodoCarga
    filas_extraidas: int
    filas_staging_tras_limpieza: int
    filas_eliminadas_destino: int
    filas_cargadas_destino: int
    filas_ejecutivo_normalizadas: int
