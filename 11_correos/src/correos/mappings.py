"""Constantes de negocio: tablas de destino en SQL Server ('CL_MOVIL') y las
columnas esperadas de cada hoja de los 'Registro_*.xlsx' consolidados desde
'14 CORREOS' (ver consolidar.py)."""

from __future__ import annotations

ESQUEMA = "dbo"
TABLA_REGISTRO = "TBL_CORREO_REGISTRO"
TABLA_BANDEJAS = "TBL_CORREO_BANDEJAS"

# Campo usado como criterio de carga incremental/por periodo en TBL_CORREO_REGISTRO
# (ver consolidar.preparar_registro: se convierte de texto ISO-8601 UTC a datetime).
COLUMNA_CONTROL_FECHA = "FechaHora_UTC_Texto"

COLUMNAS_REGISTRO = [
    "Bandeja",
    "Tipo",
    "FechaHora_UTC_Texto",
    "FechaHora",
    "Contacto",
    "Asunto",
    "ID_Mensaje",
    "ConversationID",
    "Asesor",
    "EsPrimeraEntrada",
    "TieneRespuesta",
    "Tiempo_Primera_Respuesta_Horas",
    "Estado",
    "Tiempo_Respuesta_Horas",
]

COLUMNAS_BANDEJAS = [
    "Correo_Bandeja",
    "Asesor",
    "UltimaRevisionEntrada",
    "UltimaRevisionSalida",
]

# Columna que identifica una fila real (no una fila de plantilla sin usar:
# cada Registro_*.xlsx trae una hoja 'Registro' pre-formateada a 5000 filas,
# de las cuales solo una fraccion tiene datos reales).
COLUMNA_CLAVE_REGISTRO = "Bandeja"
COLUMNA_CLAVE_BANDEJAS = "Correo_Bandeja"

# Clave de deduplicacion defensiva antes de insertar (no se observaron
# duplicados en los datos reales, pero una re-ejecucion no deberia poder
# introducirlos).
COLUMNA_DEDUP_REGISTRO = "ID_Mensaje"
