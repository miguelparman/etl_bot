"""Column spec del Data Flow "TBL_FUNNEL_SENHALIZACIONES" (Flat File -> SQL).

Fuente: componente Flat File Source (conexion 'Senhalizaciones', archivo
Señalizaciones.csv) + Data Conversion + OLE DB Destination del paquete
CROSS 0101 SSIS_CL_Senalizaciones.dtsx.

Notas de fidelidad con el .dtsx original:
- La columna de origen 'TOTAL INGRESADO' del CSV NUNCA fue seleccionada por
  el Flat File Source original, por lo que la columna de destino homonima
  queda sin mapear (NULL) tambien aqui -- se omite intencionalmente.
- El destino 'MÚMERO DEL CUAL LLAMA' esta mal escrito en la tabla SQL
  original (falta la 'N' de NUMERO); se conserva tal cual para no romper
  compatibilidad con la tabla existente.
"""

from __future__ import annotations

from etl_chile.domain.column_spec import CastType, ColumnMapping

FUNNEL_SENALIZACIONES_TABLE = "TBL_FUNNEL_SENHALIZACIONES"

# Esquema fijo declarado por el Flat File Connection Manager 'Senhalizaciones'
# del .dtsx original (39 columnas, en orden). Se usa para asignar nombres de
# columna POR POSICION al leer el CSV (ver flat_file_reader.py) en vez de
# confiar en el texto del encabezado real del archivo, que puede cambiar si
# el CSV se regenera desde una hoja de Google Sheets editada a mano (p.ej.
# la columna 'Segmento' aparecio en minuscula y la ultima ('MES') con el
# nombre 'cccc' en una ejecucion real).
SENALIZACIONES_RAW_CSV_COLUMNS = (
    "Marca temporal",
    "Tu DNI",
    "Coordinador",
    "Rut de la Empresa",
    "Nombre Empresa",
    "Correo de la Empresa",
    "Teléfono de contacto",
    "Servicio",
    "Sub Servicio ",
    "Cantidad de líneas a contratar",
    "Comentario de venta",
    "Canal por donde ingresa la venta",
    "Número del cual llama",
    "La señalización fue Proactiva o Reactiva",
    "OPORTUNDAD MOVIL (CHI-XXXXXX)",
    "Agente",
    "Segmento",
    "STB",
    "BAF",
    "TV",
    "VOZ",
    "BAM",
    "TOTAL INGRESADO",
    "BO responsable del Caso",
    "Fecha de Gestion del BO",
    "Estado de Negociacion",
    "Motivo de Cancelacion",
    "OBS",
    "Observacion de Señalizacion",
    "Mes",
    "Dia",
    "REGION",
    "COMUNA",
    "DIRECCION",
    "1ER CONTACTO",
    "2DO CONTACTO",
    "3ER CONTACTO",
    "OBSERVACION BO",
    "MES",
)

FUNNEL_SENALIZACIONES_COLUMN_SPEC = (
    ColumnMapping("Marca temporal", "MARCA TEMPORAL", CastType.DATE),
    ColumnMapping("Tu DNI", "TU DNI", CastType.STR),
    ColumnMapping("Coordinador", "COORDINADOR", CastType.STR),
    ColumnMapping("Rut de la Empresa", "RUT DE LA EMPRESA", CastType.STR),
    ColumnMapping("Nombre Empresa", "NOMBRE EMPRESA", CastType.STR),
    ColumnMapping("Correo de la Empresa", "CORREO DE LA EMPRESA", CastType.STR),
    ColumnMapping("Servicio", "SERVICIO", CastType.STR),
    ColumnMapping("Sub Servicio ", "SUB SERVICIO", CastType.STR),
    ColumnMapping("Comentario de venta", "COMENTARIO DE VENTA", CastType.STR),
    ColumnMapping(
        "Canal por donde ingresa la venta", "CANAL POR DONDE INGRESA LA VENTA", CastType.STR
    ),
    ColumnMapping("Mes", "MES", CastType.STR),
    ColumnMapping("OBS", "OBS", CastType.STR),
    ColumnMapping("Motivo de Cancelacion", "MOTIVO DE CANCELACION", CastType.STR),
    ColumnMapping("Estado de Negociacion", "ESTADO DE NEGOCIACION", CastType.STR),
    ColumnMapping("Fecha de Gestion del BO", "FECHA DE GESTION DEL BO", CastType.DATE),
    ColumnMapping("BO responsable del Caso", "BO RESPONSABLE DEL CASO", CastType.STR),
    ColumnMapping("BAM", "BAM", CastType.FLOAT),
    ColumnMapping("VOZ", "VOZ", CastType.FLOAT),
    ColumnMapping("TV", "TV", CastType.FLOAT),
    ColumnMapping("BAF", "BAF", CastType.FLOAT),
    ColumnMapping("STB", "STB", CastType.FLOAT),
    ColumnMapping("Segmento", "SEGMENTO", CastType.STR),
    ColumnMapping("Agente", "AGENTE", CastType.STR),
    ColumnMapping(
        "La señalización fue Proactiva o Reactiva",
        "LA SEÑALIZACION FUE PROACTIVA O REACTIVA",
        CastType.STR,
    ),
    # sic: destino mal escrito en la tabla original ("MÚMERO" en vez de "NÚMERO")
    ColumnMapping("Número del cual llama", "MÚMERO DEL CUAL LLAMA", CastType.STR),
    ColumnMapping("Observacion de Señalizacion", "OBSERVACION DE SEÑALIZACION", CastType.STR),
    ColumnMapping(
        "Cantidad de líneas a contratar", "CANTIDAD DE LÍNEAS A CONTRATAR", CastType.STR
    ),
    ColumnMapping("Teléfono de contacto", "TELÉFONO DE CONTACTO", CastType.STR),
    ColumnMapping("OBSERVACION BO", "OBSERVACION BO", CastType.STR),
    ColumnMapping("3ER CONTACTO", "3ER CONTACTO", CastType.DATE),
    ColumnMapping("2DO CONTACTO", "2DO CONTACTO", CastType.DATE),
    ColumnMapping("1ER CONTACTO", "1ER CONTACTO", CastType.DATE),
    ColumnMapping("DIRECCION", "DIRECCION", CastType.STR),
    ColumnMapping("COMUNA", "COMUNA", CastType.STR),
    ColumnMapping("REGION", "REGION", CastType.STR),
    # 'TOTAL INGRESADO' se omite deliberadamente (ver docstring del modulo).
)
