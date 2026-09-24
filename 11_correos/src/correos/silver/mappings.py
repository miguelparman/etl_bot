"""Constantes de la capa SILVER (ver cargar.py): tablas destino, columnas que
se toman de bronze y reglas de ASUNTO_AGRUPADO."""

from __future__ import annotations

from bronze.mappings import COLUMNA_CONTROL_FECHA, COLUMNA_ORIGEN, COLUMNAS_BANDEJAS, COLUMNAS_REGISTRO

ESQUEMA = "dbo"
TABLA_REGISTRO_SILVER = "TBL_CORREO_REGISTRO_SILVER"
TABLA_BANDEJAS_SILVER = "TBL_CORREO_BANDEJAS_SILVER"
COLUMNA_ASUNTO_AGRUPADO = "ASUNTO_AGRUPADO"
# Nombre del coordinador, derivado de ORIGEN (cada .xlsx es el control de un
# coordinador: 'Registro_JHON_MORALES_PENA.xlsx' -> 'JHON MORALES PENA').
COLUMNA_COORDINADOR = "COORDINADOR"

# Mismo campo de control de periodo que bronze (silver conserva el nombre):
# se re-exporta para que gold lea todo lo de silver desde aqui, sin importar
# bronze.
COLUMNA_CONTROL_FECHA = COLUMNA_CONTROL_FECHA

# TBL_CORREO_BANDEJAS_SILVER: todas las columnas de bronze + COORDINADOR.
# Se reemplaza completa en cada corrida, igual que en bronze (es el estado
# actual de cada bandeja, no un historial).
COLUMNAS_BANDEJAS_SILVER_DESDE_BRONZE = [*COLUMNAS_BANDEJAS, COLUMNA_ORIGEN]

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
