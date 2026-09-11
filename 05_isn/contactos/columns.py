"""
Definición de columnas del Data Flow "TBL_CONTACTOS_AUTORIZADOS_CHILE" del
paquete SSIS_CL_ISN_Contactos.dtsx.

IMPORTANTE: el Connection Manager FLATFILE declara los nombres de columna
"No  identificación fiscal" (dos espacios), "Id  de contacto" (dos espacios),
pero el CSV real (verificado contra el archivo en producción) trae la
cabecera "No. identificación fiscal" (con punto) e "Id. de contacto" (con
punto) -- SSIS no usa el texto de la cabecera para mapear columnas cuando
`ColumnNamesInFirstDataRow=True`, solo la salta; el mapeo real es posicional,
contra el esquema fijo del Connection Manager. Por eso acá también se mapea
por POSICIÓN, no por nombre de cabecera, para no depender de esa cabecera.

Orden verificado contra el archivo real
(Reporte_Contactos_Salesforce_BI.csv, 19 columnas).
"""
from __future__ import annotations

# Nombres de columna de origen, en el orden posicional real del CSV.
COLUMNAS_ORIGEN = [
    "No  identificación fiscal",
    "Nombre del cliente",
    "Segmento Global",
    "Subsegmento local",
    "Número de documento",
    "Nombre",
    "Apellidos",
    "Cargo",
    "Teléfono",
    "Móvil",
    "Correo electrónico",
    "Autorizaciones funcionales",
    "Acceso a Portal Platino",
    "Representante legal",
    "Fecha de creación",
    "Fecha de la última modificación",
    "Creado por",
    "Última modificación por",
    "Id  de contacto",
]

# Columnas de texto (Data Convert -> wstr) tal cual, sin casteo numérico/fecha.
COLUMNAS_TEXTO = [
    "No  identificación fiscal",
    "Nombre del cliente",
    "Segmento Global",
    "Subsegmento local",
    "Número de documento",
    "Nombre",
    "Apellidos",
    "Cargo",
    "Teléfono",
    "Móvil",
    "Correo electrónico",
    "Autorizaciones funcionales",
    "Creado por",
    "Última modificación por",
    "Id  de contacto",
]

# Anchos máximos por columna de texto en el Data Convert original (verificado
# columna por columna en el .dtsx: atributo 'length' de cada outputColumn).
# Para la mayoría, errorRowDisposition/truncationRowDisposition="FailComponent"
# -- si un valor no entra, SSIS frena todo el Data Flow -- así que
# validator.py debe rechazar la fila en vez de dejar que trunque silenciosamente
# (y, en el peor caso, reviente contra SQL Server como pasó en producción con
# TELÉFONO antes de que esta columna se identificara como IgnoreFailure).
ANCHOS_MAXIMOS_TEXTO = {
    "No  identificación fiscal": 20,
    "Nombre del cliente": 300,
    "Segmento Global": 50,
    "Subsegmento local": 30,
    "Número de documento": 30,
    "Nombre": 50,
    "Apellidos": 100,
    "Cargo": 100,
    "Teléfono": 20,
    "Móvil": 20,
    "Correo electrónico": 80,
    "Autorizaciones funcionales": 500,
    "Creado por": 80,
    "Última modificación por": 80,
    "Id  de contacto": 30,
}

# Estas 4 sí tienen errorRowDisposition/truncationRowDisposition="IgnoreFailure"
# en el .dtsx: SSIS trunca el valor en silencio y sigue, en vez de frenar el
# Data Flow. Confirmado con datos reales: un TELÉFONO de producción
# ("Nelson: 56 9 53068855", 21 caracteres) excede el ancho de 20 y SSIS lo
# habría truncado sin más -- acá se replica ese truncamiento silencioso.
COLUMNAS_TRUNCAR_SILENCIOSO = {"Cargo", "Teléfono", "Móvil", "Última modificación por"}

# El resto de ANCHOS_MAXIMOS_TEXTO es FailComponent: si un valor excede el
# ancho, la fila se rechaza en validator.py en vez de truncarla.
COLUMNAS_FALLAR_SI_EXCEDE = [c for c in ANCHOS_MAXIMOS_TEXTO if c not in COLUMNAS_TRUNCAR_SILENCIOSO]

# Columnas Data Convert -> r4 (float) en SSIS, pero la columna destino real
# (OLE DB Destination external column) es i4 (entero) -- se castea directo a
# entero anulable en Python, el resultado final en la tabla es el mismo.
COLUMNAS_ENTERAS = ["Acceso a Portal Platino", "Representante legal"]

# Columnas Data Convert -> date.
COLUMNAS_FECHA = ["Fecha de creación", "Fecha de la última modificación"]

# Mapeo columna origen -> columna destino en
# [CL_ANALISIS].[dbo].[TBL_CONTACTOS_AUTORIZADOS_CHILE], confirmado contra
# el input de las OLE DB Destination external columns del .dtsx.
MAPEO_DESTINO = {
    "No  identificación fiscal": "RUC",
    "Nombre del cliente": "NOMBRE CLIENTE",
    "Segmento Global": "SEGMENTO GLOBAL",
    "Subsegmento local": "SUBSEGMENTO LOCAL",
    "Número de documento": "NÚMERO DOCUMENTO",
    "Nombre": "NOMBRE",
    "Apellidos": "APELLIDOS",
    "Cargo": "CARGO",
    "Teléfono": "TELÉFONO",
    "Móvil": "MÓVIL",
    "Correo electrónico": "CORREO ELECTRÓNICO",
    "Autorizaciones funcionales": "AUTORIZACIONES FUNCIONALES",
    "Acceso a Portal Platino": "ACCESO PLATINO",
    "Representante legal": "REPRESENTANTE LEGAL",
    "Fecha de creación": "FECHA CREACIÓN",
    "Fecha de la última modificación": "FECHA MODIFICACIÓN",
    "Creado por": "CREADO POR",
    "Última modificación por": "ÚLTIMA  MODIFICACIÓN POR",  # dos espacios: así está el external column real (verificado en el .dtsx)
    "Id  de contacto": "ID CONTACTO",
}

TABLA_DESTINO = "TBL_CONTACTOS_AUTORIZADOS_CHILE"
TABLA_NUMEROS = "TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS"
