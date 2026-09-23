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

# Columna agregada en TBL_CORREO_REGISTRO y TBL_CORREO_BANDEJAS (no viene en
# las hojas): nombre del .xlsx de '14 CORREOS' del que se leyo cada fila (ver
# consolidar.py).
COLUMNA_ORIGEN = "ORIGEN"

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

# --- Capa silver (ver silver.py): TBL_CORREO_REGISTRO (bronze) + columnas derivadas.
TABLA_REGISTRO_SILVER = "TBL_CORREO_REGISTRO_SILVER"
COLUMNA_ASUNTO_AGRUPADO = "ASUNTO_AGRUPADO"

# Columnas de bronze que NO pasan a silver (ni a gold): son calculos que hace
# la macro del Excel y no son confiables (ej. Tiempo_Respuesta_Horas ~1.110.900
# h = tiempo desde la fecha 0 de Excel cuando no encuentra la entrada;
# Tiempo_Primera_Respuesta_Horas negativo; Estado siempre vacio). Quedan solo
# en bronze, tal cual llegan.
COLUMNAS_EXCLUIDAS_SILVER = [
    "EsPrimeraEntrada",
    "TieneRespuesta",
    "Tiempo_Primera_Respuesta_Horas",
    "Estado",
    "Tiempo_Respuesta_Horas",
]
COLUMNAS_SILVER_DESDE_BRONZE = [
    *[c for c in COLUMNAS_REGISTRO if c not in COLUMNAS_EXCLUIDAS_SILVER],
    COLUMNA_ORIGEN,
]

# Reglas de ASUNTO_AGRUPADO, evaluadas EN ORDEN (gana la primera que calza):
# (grupo, textos, palabra_completa). Si 'Asunto' contiene alguno de los
# textos, se asigna ese grupo. Con palabra_completa=True el texto debe
# aparecer como palabra(s) completa(s) -- ej. 'presentacion' NO calza dentro
# de 'representacion'; con False basta que aparezca en cualquier parte.
# Sin distinguir mayusculas ni tildes (ver silver._normalizar). Un asunto que
# no calza ninguna queda NULL. REBOTE va primero: un rebote puede citar el
# asunto original (ej. 'No entregable: Actualizacion de correo de contacto
# ...') y debe contarse como rebote, no como PRESENTACION.
REGLAS_ASUNTO_AGRUPADO: list[tuple[str, list[str], bool]] = [
    (
        "REBOTE",
        [
            "delivery status notification",
            "notificacion de estado de entrega",
            "no entregable:",
            "undelivered mail returned to sender",
        ],
        False,
    ),
    ("PRESENTACIÓN", ["actualizacion de correo de contacto", "presentacion"], True),
    # Texto parcial a proposito: cubre 'pruebaaa', 'PRUEBA17/09', etc.
    ("PRUEBA", ["prueba"], False),
    # 'promo' a secas: cubre PROMOSEPTIEMBRE, PROMOSETIEMBRE, 'PROMO SEPTIEMBRE',
    # 'PROMOCIONES', etc.
    ("PROMO", ["promo"], False),
]

# --- Capa gold (ver gold.py): modelo estrella en su propio esquema.
ESQUEMA_GOLD = "gold"
TABLA_FACT_MENSAJE = "FACT_MENSAJE"
TABLA_DIM_FECHA = "DIM_FECHA"
TABLA_DIM_BANDEJA = "DIM_BANDEJA"
TABLA_DIM_TIPO = "DIM_TIPO"
TABLA_DIM_ASUNTO_AGRUPADO = "DIM_ASUNTO_AGRUPADO"

# Desfase fijo de la hora local Peru/Bogota (sin horario de verano) respecto
# de UTC. Solo se usa como respaldo si 'FechaHora' (ya local) viniera vacia.
DESFASE_HORAS_LOCAL = -5
