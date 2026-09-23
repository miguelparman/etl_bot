"""Constantes de la capa SILVER (ver cargar.py): tabla destino, columnas que
se toman de bronze y reglas de ASUNTO_AGRUPADO."""

from __future__ import annotations

from bronze.mappings import COLUMNA_ORIGEN, COLUMNAS_REGISTRO

ESQUEMA = "dbo"
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
# Sin distinguir mayusculas ni tildes (ver cargar._normalizar). Un asunto que
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
