"""Excepciones del proceso de copia de tablas. No dependen de pyodbc, pandas
ni ninguna otra libreria externa."""

from __future__ import annotations


class CopiaTablaError(Exception):
    """Error al copiar el esquema o los datos de una tabla del servidor
    origen hacia el servidor destino."""
