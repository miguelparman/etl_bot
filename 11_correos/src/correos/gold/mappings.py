"""Constantes de la capa GOLD (ver cargar.py / sql.py): modelo estrella en
su propio esquema."""

from __future__ import annotations

ESQUEMA_GOLD = "gold"
TABLA_FACT_MENSAJE = "FACT_MENSAJE"
TABLA_DIM_FECHA = "DIM_FECHA"
TABLA_DIM_BANDEJA = "DIM_BANDEJA"
TABLA_DIM_TIPO = "DIM_TIPO"
TABLA_DIM_ASUNTO_AGRUPADO = "DIM_ASUNTO_AGRUPADO"

# Desfase fijo de la hora local Peru/Bogota (sin horario de verano) respecto
# de UTC. Solo se usa como respaldo si 'FechaHora' (ya local) viniera vacia.
DESFASE_HORAS_LOCAL = -5
