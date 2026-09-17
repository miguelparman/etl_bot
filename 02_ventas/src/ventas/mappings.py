"""Constantes de negocio migradas literalmente de los .dtsx originales:
nombres de archivo/hoja de SharePoint, tablas destino, columnas y anchos de
truncamiento (ColumnaSpec.estricto replica la disposicion de error
FailComponent/IgnoreFailure de cada componente -- ver README, "Notas de
fidelidad")."""

from __future__ import annotations

from models import ColumnaSpec

# ---------------------------------------------------------------------------
# SharePoint (carpeta '07 CROSS' -- ver README, "Alcance de origenes")
# ---------------------------------------------------------------------------

# exportar_senhalizaciones_csv.py corrio de nuevo el 2026-09-16 y regenero
# 'Señalizaciones.csv' en '07 CROSS' con ';' como delimitador (ver ese
# script). Antes usaba ',' (default de csv.writer sin 'delimiter' explicito).
CSV_DELIMITER = ";"

ARCHIVO_SENHALIZACIONES_CSV = "Señalizaciones.csv"
ARCHIVO_BASE_CARTA_META_XLSX = "Base Carta Meta.xlsx"
HOJA_DNI_SENALIZACIONES = "DNI Senalizaciones"

# exportar_senhalizaciones_csv.py (paso 0, junto con copiar_funnel_ventas.py):
# descarga el CSV publicado de Google Sheets/Forms (recibe respuestas del
# formulario de señalizaciones) y lo sube a '07 CROSS' como
# 'Señalizaciones.csv'. Reemplaza al Execute Process Task 'Descargar
# googledrive señalizaciones' del .dtsx original, que llamaba a este mismo
# script (entonces ubicado en 02_Cross/Ch_Senhalizaciones.py, y escribia a
# una ruta de red local en vez de subir a SharePoint).
URL_GOOGLE_SHEETS_SENHALIZACIONES = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGvrMy0rZHCWd7U4g7zN0h1S-sF_Shb4b8AOHz1FwK61rXBYDW_ZJ9yBIaky3AAzKRSwHPvql71N2Q/"
    "pub?gid=459395871&single=true&output=csv"
)
# El .dtsx original (Flat File Connection Manager) declara 39 columnas para
# 'Señalizaciones.csv' -- el formulario de Google puede traer columnas
# adicionales agregadas a mano con el tiempo; se recortan a las primeras 39
# igual que hacia Ch_Senhalizaciones.py originalmente.
NUM_COLUMNAS_SENHALIZACIONES_CSV = 39

# ---------------------------------------------------------------------------
# CROSS 0101 SSIS_CL_Senalizaciones.dtsx -- destino CL_USUARIOS
# ---------------------------------------------------------------------------

TABLA_SENHALIZACIONES_DNI = "TBL_FUNNEL_SENHALIZACIONES_DNI"
TABLA_SENHALIZACIONES = "TBL_FUNNEL_SENHALIZACIONES"
SP_FUNNEL_SENHALIZACIONES = "SP_FUNNEL_SENHALIZACIONES"

# Origen Excel 'DNI Senalizaciones$' -> Data Convert -> Destino
# TBL_FUNNEL_SENHALIZACIONES_DNI. Las 3 columnas son FailComponent tanto en
# el Origen Excel como en el Data Convert (estricto=True en ambos casos).
COLUMNAS_SENHALIZACIONES_DNI = (
    ColumnaSpec("DNI ORIGEN", 15, estricto=True),
    ColumnaSpec("DNI A CAMBIAR", 15, estricto=True),
    ColumnaSpec("Observación", 255, estricto=True),
)

# Mismas 3 columnas/tabla, reutilizadas por Ventas (Contenedor de secuencias
# 2\Contenedor de secuencias 1): el .dtsx de Ventas recarga esta MISMA tabla
# de forma independiente del paquete de Señalizaciones -- ver README, "Notas
# de fidelidad" (redundancia intencional preservada, no deduplicada).

# Origen Flat File 'Señalizaciones.csv' -> Data Convert -> Destino
# TBL_FUNNEL_SENHALIZACIONES. Nombre de columna origen -> nombre de columna
# fisica destino (columna a columna, orden del mapeo original). El nombre
# destino 'MÚMERO DEL CUAL LLAMA' preserva un typo real de la tabla SQL
# ('MÚ' en vez de 'NÚ') -- no se corrige, ver README.
#
# 'estricto' replica la disposicion FailComponent del Data Convert (que es
# la unica capa que puede fallar realmente por ancho de columna de texto,
# ver README): FailComponent para todas las columnas de TEXTO, salvo que
# tambien se excluyen aqui las columnas NUMERICAS/FECHA (STB/BAF/TV/VOZ/BAM,
# fechas) porque para esas el ancho no aplica -- su disposicion real es la
# del Origen Flat File (IgnoreFailure: valor invalido -> NULL, sin abortar),
# implementada en transformer.py via pd.to_numeric/pd.to_datetime(errors="coerce").
COLUMNAS_SENHALIZACIONES = (
    ColumnaSpec("MARCA TEMPORAL", estricto=False, tipo="fecha"),
    ColumnaSpec("TU DNI", 15, estricto=True),
    ColumnaSpec("COORDINADOR", 50, estricto=True),
    ColumnaSpec("RUT DE LA EMPRESA", 15, estricto=True),
    ColumnaSpec("NOMBRE EMPRESA", 100, estricto=True),
    ColumnaSpec("CORREO DE LA EMPRESA", 50, estricto=True),
    ColumnaSpec("SERVICIO", 50, estricto=True),
    ColumnaSpec("SUB SERVICIO", 50, estricto=True),
    ColumnaSpec("COMENTARIO DE VENTA", 800, estricto=True),
    ColumnaSpec("CANAL POR DONDE INGRESA LA VENTA", 50, estricto=True),
    ColumnaSpec("MES", 50, estricto=True),
    ColumnaSpec("OBS", 200, estricto=True),
    ColumnaSpec("MOTIVO DE CANCELACION", 50, estricto=True),
    ColumnaSpec("ESTADO DE NEGOCIACION", 50, estricto=True),
    ColumnaSpec("FECHA DE GESTION DEL BO", estricto=False, tipo="fecha"),
    ColumnaSpec("BO RESPONSABLE DEL CASO", 50, estricto=True),
    ColumnaSpec("BAM", estricto=False, tipo="numero"),
    ColumnaSpec("VOZ", estricto=False, tipo="numero"),
    ColumnaSpec("TV", estricto=False, tipo="numero"),
    ColumnaSpec("BAF", estricto=False, tipo="numero"),
    ColumnaSpec("STB", estricto=False, tipo="numero"),
    ColumnaSpec("SEGMENTO", 50, estricto=True),
    ColumnaSpec("AGENTE", 50, estricto=True),
    ColumnaSpec("LA SEÑALIZACION FUE PROACTIVA O REACTIVA", 50, estricto=True),
    ColumnaSpec("MÚMERO DEL CUAL LLAMA", 50, estricto=True),
    ColumnaSpec("OBSERVACION DE SEÑALIZACION", 800, estricto=True),
    ColumnaSpec("CANTIDAD DE LÍNEAS A CONTRATAR", 10, estricto=True),
    ColumnaSpec("TELÉFONO DE CONTACTO", 50, estricto=True),
    ColumnaSpec("OBSERVACION BO", 800, estricto=True),
    ColumnaSpec("3ER CONTACTO", estricto=False, tipo="fecha"),
    ColumnaSpec("2DO CONTACTO", estricto=False, tipo="fecha"),
    ColumnaSpec("1ER CONTACTO", estricto=False, tipo="fecha"),
    ColumnaSpec("DIRECCION", 50, estricto=True),
    ColumnaSpec("COMUNA", 50, estricto=True),
    ColumnaSpec("REGION", 50, estricto=True),
)

# Columna origen (CSV) -> columna destino (tabla), en el mismo orden que
# COLUMNAS_SENHALIZACIONES arriba. Las columnas del CSV no listadas aqui
# (TOTAL INGRESADO, Dia, MES [ultima], OPORTUNDAD MOVIL (CHI-XXXXXX)) se leen
# pero se descartan, igual que en el .dtsx original. 'Sub Servicio' en el
# .dtsx original tenia un espacio final literal ('Sub Servicio ') -- ya no
# aplica: exportar_senhalizaciones_csv.py aplica trim tambien al encabezado.
MAPEO_SENHALIZACIONES: tuple[tuple[str, str], ...] = (
    ("Marca temporal", "MARCA TEMPORAL"),
    ("Tu DNI", "TU DNI"),
    ("Coordinador", "COORDINADOR"),
    ("Rut de la Empresa", "RUT DE LA EMPRESA"),
    ("Nombre Empresa", "NOMBRE EMPRESA"),
    ("Correo de la Empresa", "CORREO DE LA EMPRESA"),
    ("Servicio", "SERVICIO"),
    ("Sub Servicio", "SUB SERVICIO"),
    ("Comentario de venta", "COMENTARIO DE VENTA"),
    ("Canal por donde ingresa la venta", "CANAL POR DONDE INGRESA LA VENTA"),
    ("Mes", "MES"),
    ("OBS", "OBS"),
    ("Motivo de Cancelacion", "MOTIVO DE CANCELACION"),
    ("Estado de Negociacion", "ESTADO DE NEGOCIACION"),
    ("Fecha de Gestion del BO", "FECHA DE GESTION DEL BO"),
    ("BO responsable del Caso", "BO RESPONSABLE DEL CASO"),
    ("BAM", "BAM"),
    ("VOZ", "VOZ"),
    ("TV", "TV"),
    ("BAF", "BAF"),
    ("STB", "STB"),
    ("Segmento", "SEGMENTO"),
    ("Agente", "AGENTE"),
    ("La señalización fue Proactiva o Reactiva", "LA SEÑALIZACION FUE PROACTIVA O REACTIVA"),
    ("Número del cual llama", "MÚMERO DEL CUAL LLAMA"),
    ("Observacion de Señalizacion", "OBSERVACION DE SEÑALIZACION"),
    ("Cantidad de líneas a contratar", "CANTIDAD DE LÍNEAS A CONTRATAR"),
    ("Teléfono de contacto", "TELÉFONO DE CONTACTO"),
    ("OBSERVACION BO", "OBSERVACION BO"),
    ("3ER CONTACTO", "3ER CONTACTO"),
    ("2DO CONTACTO", "2DO CONTACTO"),
    ("1ER CONTACTO", "1ER CONTACTO"),
    ("DIRECCION", "DIRECCION"),
    ("COMUNA", "COMUNA"),
    ("REGION", "REGION"),
)

# Correcciones literales de 'TU DNI' con cero(s) inicial(es) perdido(s)
# (Execute SQL Task 'UPDATE' del Contenedor de secuencias 1, 19 sentencias
# separadas por 'GO' en el .dtsx original -- 'GO' no es SQL valido para el
# proveedor OLEDB del Execute SQL Task, asi que aqui se preservan como pares
# (dni_correcto, dni_incorrecto) parametrizados, ver sql.py). El par
# ('004981615', '4981615') aparece dos veces en el .dtsx original (no-op
# redundante) -- se preserva tal cual.
CORRECCIONES_DNI_CEROS: tuple[tuple[str, str], ...] = (
    ("002577992", "2577992"),
    ("003323113", "3323113"),
    ("003328048", "3328048"),
    ("003343872", "3343872"),
    ("003460521", "3460521"),
    ("003686853", "3686853"),
    ("003814303", "3814303"),
    ("004111606", "4111606"),
    ("004981615", "4981615"),
    ("004981615", "4981615"),
    ("005832728", "5832728"),
    ("06034261", "6034261"),
    ("07215509", "7215509"),
    ("007519207", "7519207"),
    ("07528394", "7528394"),
    ("08817881", "8817881"),
    ("09344499", "9344499"),
    ("09399377", "9399377"),
    ("09488600", "9488600"),
)

# ---------------------------------------------------------------------------
# CROSS 0102 SSIS_CL_Ventas.dtsx -- destino CL_USUARIOS ('162.CL_DATA' esta
# declarado en el .dtsx original pero ningun Data Flow/Execute SQL Task lo
# usa -- no se migra ninguna conexion a CL_DATA, ver README).
# ---------------------------------------------------------------------------

ARCHIVO_FUNNEL_VENTAS_XLSX = "FUNNEL VENTAS V2.xlsx"
HOJA_BASEV2 = "baseV2"
HOJA_ESP = "Esp"
HOJA_SUP = "Sup"
# Ambas hojas siguientes viven en 'Base Carta Meta.xlsx' (no en FUNNEL VENTAS
# V2.xlsx) -- confirmado por el connectionManagerRefId de cada Origen Excel
# en el .dtsx original.
HOJA_COMISIONES_MES = "Comisiones mes"
HOJA_METAS = "Hoja1"

TABLA_VENTAS_BASEV2_TEMP = "TBL_FUNNEL_VENTAS_basev2_temp"
TABLA_VENTAS_ESP_TEMP = "TBL_FUNNEL_VENTAS_Esp_temp"
TABLA_VENTAS_SUP_TEMP = "TBL_FUNNEL_VENTAS_Sup_temp"
TABLA_VENTAS_RANGO_COMISIONES = "TBL_VENTAS_RANGO_COMISIONES"
TABLA_METAS_COMISIONES = "METAS_COMISIONES"
TABLA_VENTAS_TEMP = "TBL_FUNNEL_VENTAS_Temp"
TABLA_VENTAS2 = "TBL_FUNNEL_VENTAS2"

# Origen Excel 'baseV2$' (FUNNEL VENTAS V2.xlsx) -> Data Convert -> Destino
# TBL_FUNNEL_VENTAS_basev2_temp. El Data Convert mapea 'Copy of X' 1:1 a la
# columna destino 'X' (sin renombrar) -- por eso aqui basta una lista de
# ColumnaSpec, no un mapeo origen/destino como en Señalizaciones.
#
# 'estricto=False' replica las columnas marcadas 'IgnoreFailure' en el
# Data Convert original (ver README); el resto son 'FailComponent' (default).
COLUMNAS_VENTAS_BASEV2 = (
    ColumnaSpec("Fecha Ingreso", estricto=True, tipo="fecha"),
    ColumnaSpec("Tramo Ingreso", 15, estricto=True),  # fecha origen -> texto destino (asi es en el .dtsx original)
    ColumnaSpec("Rut Empresa", 15, estricto=True),
    ColumnaSpec("Segmento", 25, estricto=True),
    ColumnaSpec("Servicio", 25, estricto=True),
    ColumnaSpec("Sub Servicio", 25, estricto=True),
    ColumnaSpec("STB", estricto=True, tipo="numero"),
    ColumnaSpec("BAF", estricto=True, tipo="numero"),
    ColumnaSpec("TV", estricto=True, tipo="numero"),
    ColumnaSpec("VOZ", estricto=True, tipo="numero"),
    ColumnaSpec("BAM", estricto=True, tipo="numero"),
    ColumnaSpec("TOTAL INGRESADO", estricto=True, tipo="numero"),
    ColumnaSpec("ESTADO", 15, estricto=True),
    ColumnaSpec("MODALIDAD DE INGRESO", 15, estricto=False),
    ColumnaSpec("MOTIVO CANCELACION", 455, estricto=False),
    ColumnaSpec("OBS SEGUIMIENTO", 125, estricto=False),
    ColumnaSpec("TIPO VENTA", 25, estricto=False),
    ColumnaSpec("OBSERVACION", 455, estricto=True),
    ColumnaSpec("Nro de Orden DEM/BELIEVE", 55, estricto=False),
    ColumnaSpec("NRO ENGANCHE", 55, estricto=False),
    ColumnaSpec("FECHA HABILITACION", estricto=False, tipo="fecha"),
    ColumnaSpec("FECHA ENGANCHE", estricto=False, tipo="fecha"),
    ColumnaSpec("RUT BACK", 15, estricto=True),
    ColumnaSpec("BACKOFFICE", 125, estricto=True),
    ColumnaSpec("RUT RAC VENTA", 15, estricto=True),
    ColumnaSpec("SEÑALIZACION // EJECUTIVO DE VENTAS", 15, estricto=False),
    ColumnaSpec("RUT EJECUTIVO", 15, estricto=False),
    ColumnaSpec("NOMBRE EJECUTIVO", 125, estricto=True),
    ColumnaSpec("SUB SEGMENTO", 15, estricto=False),
    ColumnaSpec("SUPERVISOR", 125, estricto=True),
    ColumnaSpec("Especialista", 125, estricto=True),
    ColumnaSpec("Pusher", 125, estricto=True),
    ColumnaSpec("AUDITORIA AUTOINGRESO", 15, estricto=False),
    ColumnaSpec("Nombre Empresa", 255, estricto=False),
)

# Origen Excel 'Esp$' (FUNNEL VENTAS V2.xlsx) -> Destino TBL_FUNNEL_VENTAS_Esp_temp.
COLUMNAS_VENTAS_ESP = (
    ColumnaSpec("DNI", 15, estricto=True),
    ColumnaSpec("Especialista", 125, estricto=True),
)

# Origen Excel 'Sup$' (FUNNEL VENTAS V2.xlsx) -> Destino TBL_FUNNEL_VENTAS_Sup_temp.
COLUMNAS_VENTAS_SUP = (
    ColumnaSpec("DNI", 15, estricto=True),
    ColumnaSpec("SUPERVISOR", 125, estricto=True),
)

# Origen Excel 'Comisiones mes$' (Base Carta Meta.xlsx) -> Destino
# TBL_VENTAS_RANGO_COMISIONES. Sin Data Convert en el .dtsx original: las 20
# columnas pasan directo, mismo nombre, sin casteo -- se listan solo para
# validar que existan en el origen (ColumnaSpec generico, sin ancho).
COLUMNAS_VENTAS_RANGO_COMISIONES = (
    "PERIODO", "CARGO",
    "META_1", "FO_1", "STB_1", "TV_1", "BAM_1", "VOZ_1",
    "META_2", "FO_2", "STB_2", "TV_2", "BAM_2", "VOZ_2",
    "META_3", "FO_3", "STB_3", "TV_3", "BAM_3", "VOZ_3",
)

# Origen Excel 'Hoja1$' (Base Carta Meta.xlsx) -> Data Convert parcial ->
# Destino METAS_COMISIONES. 'Fibra'/'Voz'/'Total'/'Señalizacion Total' NO
# pasan por el Data Convert en el .dtsx original (van directo del Origen al
# Destino); aqui se castean igual a numero porque la tabla destino los
# declara 'int' (Fibra/Voz/Total) -- ver README, "Notas de fidelidad".
COLUMNAS_VENTAS_METAS_TEXTO = (
    ColumnaSpec("Plataforma", 255, estricto=True),
    ColumnaSpec("Cargo", 255, estricto=True),
    ColumnaSpec("Nombre", 255, estricto=True),
    ColumnaSpec("BG_DNI", 20, estricto=True),
    ColumnaSpec("DNI", 15, estricto=True),
    ColumnaSpec("PUSHER A CARGO", 55, estricto=True),
)
COLUMNAS_VENTAS_METAS_NUMERICAS = ("Fibra", "Voz", "Total", "PERIODO")
# 'Señalizacion Total' (texto en el origen) se renombra a 'SEÑALIZACIONES TOTAL'
# y se castea a entero -- la tabla destino la declara 'int'.
COLUMNA_VENTAS_METAS_SENALIZACION_TOTAL = ("Señalizacion Total", "SEÑALIZACIONES TOTAL")
# Todas las columnas que se esperan/seleccionan del origen ('Hoja1$'), antes
# de convertir_tipos_metas (que renombra 'Señalizacion Total'). La hoja real
# tiene columnas adicionales sin usar -- se filtran explicitamente con esta
# lista (ver transformer.seleccionar_columnas), igual que se hace con
# COLUMNAS_VENTAS_RANGO_COMISIONES.
COLUMNAS_VENTAS_METAS_ORIGEN = (
    tuple(c.nombre for c in COLUMNAS_VENTAS_METAS_TEXTO) + COLUMNAS_VENTAS_METAS_NUMERICAS + (COLUMNA_VENTAS_METAS_SENALIZACION_TOTAL[0],)
)

# Columnas de TBL_FUNNEL_VENTAS_basev2_temp que NO llena el Data Flow (se
# completan despues, via Execute SQL Task, ver transformacion.py).
COLUMNAS_VENTAS_BASEV2_POST_CARGA = ("DNI SUPERVISOR", "DNI ESPECIALISTA", "COD_DNI", "FECHA DE EVALUACION")

# Mapeo de columnas al pasar de TBL_FUNNEL_VENTAS_basev2_temp a
# TBL_FUNNEL_VENTAS_Temp (Data Flow 'LOCAL\TBL_FUNNEL_VENTAS_Temp', sin
# transformacion intermedia, solo Origen OLEDB -> Destino OLEDB). 'Tramo
# Ingreso' se descarga pero se descarta (no esta en esta lista a proposito).
RENOMBRE_VENTAS_BASEV2_A_TEMP: dict[str, str] = {
    "Pusher": "PUSHER",
    "DNI SUPERVISOR": "DNI supervisor",
    "DNI ESPECIALISTA": "DNI Especialista",
    "Nro de Orden DEM/BELIEVE": "Nro de Orden",
    "SEÑALIZACION // EJECUTIVO DE VENTAS": "SEÑALIZACION  EJECUTIVO DE VENTAS",
    "COD_DNI": "DNI EJECUTIVO",
}

