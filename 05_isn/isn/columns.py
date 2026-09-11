"""
Definición de columnas de los Data Flow de SSIS_CL_ISN.dtsx.

Igual que en contactos/columns.py: los Connection Manager FLATFILE declaran
"Id  del cliente" / "Id  de contacto" (dos espacios), pero los CSV reales
(verificados contra archivo en producción) traen la cabecera "Id. del
cliente" / "Id. de contacto" (con punto). El mapeo real de SSIS es
posicional (`ColumnNamesInFirstDataRow=True` solo salta la cabecera, no la
usa para mapear), así que acá también se fuerza por posición.
"""
from __future__ import annotations

# Reporte_isn_aux_cliente.csv -> TBL_ISN_SF_AUX_CLIENTE (mapeo 1:1, sin renombres)
COLUMNAS_AUX_CLIENTE = [
    "Número del caso",
    "Id  del cliente",
    "Subsector",
    "Rango de trabajadores",
    "Categoria Heredada",
    "Descripción del negocio",
]
TABLA_AUX_CLIENTE = "TBL_ISN_SF_AUX_CLIENTE"

# Reporte_isn_aux_contacto.csv -> TBL_ISN_SF_AUX_CONTACTO (mapeo 1:1, sin renombres)
COLUMNAS_AUX_CONTACTO = ["Número del caso", "Id  de contacto"]
TABLA_AUX_CONTACTO = "TBL_ISN_SF_AUX_CONTACTO"

# TBL_ISN_CALIDAD -> TBL_ISN_ENVIOS_CONSOLIDADO (Data Flow "TBL_ISN_ENVIOS_CONSOLIDADOS").
# Todas las columnas viajan 1:1 salvo dos que el Data Convert original castea
# a entero (str -> i4): FECHA_EVENTO y "Número del caso".
COLUMNAS_ENVIOS_CONSOLIDADO = [
    "FECHA_EVENTO",
    "HORA_EVENTO",
    "ANI_EVENTO",
    "ANI_CONTACTO",
    "ID_PROVEEDOR",
    "ENCUESTA",
    "NEGOCIO",
    "PROCESO_NIVEL1",
    "PROCESO_NIVEL2",
    "PROCESO_NIVEL3",
    "PROCESO_NIVEL4",
    "PROCESO_NIVEL5",
    "EMPRESA",
    "ZONA",
    "REGION",
    "COMUNA",
    "AGENCIA",
    "SUBSEGMENTO",
    "TIPO_CONTRATO",
    "PRODUCTO",
    "TECNOLOGIA",
    "RUT_CLIENTE",
    "NOMBRE_CLIENTE",
    "RUT_EJECUTIVO",
    "NOMBRE_EJECUTIVO",
    "RUT_TECNICO",
    "NOMBRE_TECNICO",
    "PCRC",
    "BASE",
    "Número del caso",
    "REFERIDO",
]
COLUMNAS_ENVIOS_CONSOLIDADO_ENTERAS = ["FECHA_EVENTO", "Número del caso"]
TABLA_ISN_CALIDAD = "TBL_ISN_CALIDAD"
TABLA_ENVIOS_CONSOLIDADO = "TBL_ISN_ENVIOS_CONSOLIDADO"

# Columnas exportadas a isn.csv (Data Flow "TBL_ISN\\EXPORT CSV"), 1:1 con TBL_ISN.
COLUMNAS_EXPORT_ISN = [
    "FECHA_EVENTO",
    "HORA_EVENTO",
    "ANI_EVENTO",
    "ANI_CONTACTO",
    "ID_PROVEEDOR",
    "ENCUESTA",
    "NEGOCIO",
    "PROCESO_NIVEL1",
    "PROCESO_NIVEL2",
    "PROCESO_NIVEL3",
    "PROCESO_NIVEL4",
    "PROCESO_NIVEL5",
    "EMPRESA",
    "ZONA",
    "REGION",
    "COMUNA",
    "AGENCIA",
    "SUBSEGMENTO",
    "TIPO_CONTRATO",
    "PRODUCTO",
    "TECNOLOGIA",
    "RUT_CLIENTE",
    "NOMBRE_CLIENTE",
    "RUT_EJECUTIVO",
    "NOMBRE_EJECUTIVO",
    "RUT_TECNICO",
    "NOMBRE_TECNICO",
    "PCRC",
]
