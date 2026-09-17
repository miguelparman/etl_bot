"""Tablas a copiar del servidor origen al servidor local. Cada entrada es la
ruta completa de 3 partes de la tabla en el origen: '[BASE].[schema].[tabla]'.
En el destino se replica con la misma base, schema y nombre.

Las tablas pueden pertenecer a bases de datos distintas dentro del mismo
servidor origen (172.17.0.162): no hace falta una conexion por base, las
consultas siempre usan la ruta completa (ver db.py).

Esta lista es el valor por defecto; se puede pasar otra en el momento con
uno o mas '--tabla' al ejecutar main.py, sin tocar este archivo."""

TABLAS_A_COPIAR: list[str] = [
    "[CL_CARTERA].[dbo].[TBL_HISTORIAL_CARTERA]",
    "[CL_CARTERA].[dbo].[TBL_CARTERA_ACTUAL]",
]
