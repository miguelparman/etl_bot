"""Puertos (interfaces) que la capa de aplicación necesita para orquestar el
caso de uso, sin conocer la tecnología concreta (pyodbc, polars, Excel, ...)
que los implementa. Las implementaciones reales viven en app/infrastructure/.

polars.DataFrame se usa como el "idioma" común de datos tabulares entre capas
(equivalente a los buffers de fila que SSIS pasa entre componentes del Data
Flow), igual que Path se usa como idioma común de rutas de archivo.
"""

from __future__ import annotations

from typing import Protocol

import polars as pl

from app.domain.models import PeriodoCarga


class ExtractorNotasCredito(Protocol):
    """Etapa 'Extract': lee y sanea el archivo de origen (Excel NC_.xlsx)."""

    def extraer(self) -> pl.DataFrame:
        """Devuelve las filas ya tipadas, listas para cargar a staging."""
        ...


class StagingRepository(Protocol):
    """Tabla de staging TBL_NC_Temp (tareas 'DELETE' y 'DELETE 2' del paquete)."""

    def truncar(self) -> None: ...

    def insertar(self, df: pl.DataFrame) -> int:
        """Inserta el DataFrame completo y devuelve la cantidad de filas insertadas."""
        ...

    def eliminar_fuera_de_periodo(self, periodo: PeriodoCarga) -> int:
        """Tarea 'DELETE': filas cuyo año y mes no coinciden con el período."""
        ...

    def eliminar_filas_invalidas(self) -> int:
        """Tarea 'DELETE 2': filas de totales/filtros del pie del reporte Excel."""
        ...

    def leer_todo(self) -> pl.DataFrame:
        """Filas restantes en staging, ya depuradas, listas para el Data Flow 'CARGA NC'."""
        ...


class DestinoRepository(Protocol):
    """Tabla final TBL_NC_DB (tareas 'DELETE NC', 'CARGA NC' y 'UPDATE' del paquete)."""

    def eliminar_periodo(self, periodo: PeriodoCarga) -> int:
        """Tarea 'DELETE NC': evita duplicados al recargar el mismo período."""
        ...

    def cargar_desde(self, df: pl.DataFrame) -> int:
        """Data Flow 'CARGA NC': inserta las filas depuradas de staging en destino."""
        ...

    def normalizar_ejecutivos(self, periodo: PeriodoCarga) -> int:
        """Tarea 'UPDATE': homologa nombres de EJECUTIVO para el período."""
        ...
