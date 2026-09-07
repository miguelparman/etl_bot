"""Column specs de los Data Flow Tasks del paquete CROSS 0102 SSIS_CL_Ventas.dtsx.

El Data Flow "TBL_FUNNEL_SENHALIZACIONES_DNI" (§5.5 de la especificacion) no
se repite aqui: es identico al del paquete de Señalizaciones y se reutiliza
desde `dni_senalizaciones_sync.py`.
"""

from __future__ import annotations

from etl_chile.domain.column_spec import CastType, ColumnMapping

# --- 5.1 TBL_FUNNEL_VENTAS_basev2_temp (hoja 'baseV2$' de FUNNEL VENTAS V2.xlsx) ---
BASEV2_SHEET = "baseV2$"
BASEV2_TABLE = "TBL_FUNNEL_VENTAS_basev2_temp"

BASEV2_COLUMN_SPEC = (
    ColumnMapping("Fecha Ingreso", "Fecha Ingreso", CastType.DATE),
    ColumnMapping("Tramo Ingreso", "Tramo Ingreso", CastType.STR),
    ColumnMapping("Rut Empresa", "Rut Empresa", CastType.STR),
    ColumnMapping("Segmento", "Segmento", CastType.STR),
    ColumnMapping("Servicio", "Servicio", CastType.STR),
    ColumnMapping("Sub Servicio", "Sub Servicio", CastType.STR),
    ColumnMapping("STB", "STB", CastType.INT),
    ColumnMapping("BAF", "BAF", CastType.INT),
    ColumnMapping("TV", "TV", CastType.INT),
    ColumnMapping("VOZ", "VOZ", CastType.INT),
    ColumnMapping("BAM", "BAM", CastType.INT),
    ColumnMapping("TOTAL INGRESADO", "TOTAL INGRESADO", CastType.INT),
    ColumnMapping("ESTADO", "ESTADO", CastType.STR),
    ColumnMapping("MODALIDAD DE INGRESO", "MODALIDAD DE INGRESO", CastType.STR),
    ColumnMapping("MOTIVO CANCELACION", "MOTIVO CANCELACION", CastType.STR),
    ColumnMapping("OBS SEGUIMIENTO", "OBS SEGUIMIENTO", CastType.STR),
    ColumnMapping("TIPO VENTA", "TIPO VENTA", CastType.STR),
    ColumnMapping("OBSERVACION", "OBSERVACION", CastType.STR),
    ColumnMapping("Nro de Orden DEM/BELIEVE", "Nro de Orden DEM/BELIEVE", CastType.STR),
    ColumnMapping("NRO ENGANCHE", "NRO ENGANCHE", CastType.STR),
    ColumnMapping("FECHA HABILITACION", "FECHA HABILITACION", CastType.DATE),
    ColumnMapping("FECHA ENGANCHE", "FECHA ENGANCHE", CastType.DATE),
    ColumnMapping("RUT BACK", "RUT BACK", CastType.STR),
    ColumnMapping("BACKOFFICE", "BACKOFFICE", CastType.STR),
    ColumnMapping("RUT RAC VENTA", "RUT RAC VENTA", CastType.STR),
    ColumnMapping(
        "SEÑALIZACION // EJECUTIVO DE VENTAS",
        "SEÑALIZACION // EJECUTIVO DE VENTAS",
        CastType.STR,
    ),
    ColumnMapping("RUT EJECUTIVO", "RUT EJECUTIVO", CastType.STR),
    ColumnMapping("NOMBRE EJECUTIVO", "NOMBRE EJECUTIVO", CastType.STR),
    ColumnMapping("SUB SEGMENTO", "SUB SEGMENTO", CastType.STR),
    ColumnMapping("SUPERVISOR", "SUPERVISOR", CastType.STR),
    ColumnMapping("Especialista", "Especialista", CastType.STR),
    ColumnMapping("Pusher", "Pusher", CastType.STR),
    ColumnMapping("AUDITORIA AUTOINGRESO", "AUDITORIA AUTOINGRESO", CastType.STR),
    ColumnMapping("Nombre Empresa", "Nombre Empresa", CastType.STR),
)

# --- 5.2 TBL_FUNNEL_VENTAS_Esp_temp (hoja 'Esp$') ---
ESP_SHEET = "Esp$"
ESP_TABLE = "TBL_FUNNEL_VENTAS_Esp_temp"

ESP_COLUMN_SPEC = (
    ColumnMapping("DNI", "DNI", CastType.STR),
    ColumnMapping("Especialista", "Especialista", CastType.STR),
)

# --- 5.3 TBL_FUNNEL_VENTAS_Sup_temp (hoja 'Sup$'; 'DNI2' del origen no se usa) ---
SUP_SHEET = "Sup$"
SUP_TABLE = "TBL_FUNNEL_VENTAS_Sup_temp"

SUP_COLUMN_SPEC = (
    ColumnMapping("DNI", "DNI", CastType.STR),
    ColumnMapping("SUPERVISOR", "SUPERVISOR", CastType.STR),
)

# --- 5.4 TBL_VENTAS_RANGO_COMISIONES (hoja 'Comisiones mes$', sin Data Conversion) ---
RANGO_COMISIONES_SHEET = "Comisiones mes$"
RANGO_COMISIONES_TABLE = "TBL_VENTAS_RANGO_COMISIONES"

RANGO_COMISIONES_COLUMN_SPEC = tuple(
    ColumnMapping(col, col, CastType.NONE)
    for col in (
        "PERIODO", "CARGO", "META_1", "FO_1", "STB_1", "TV_1", "BAM_1", "VOZ_1",
        "META_2", "FO_2", "STB_2", "TV_2", "BAM_2", "VOZ_2",
        "META_3", "FO_3", "STB_3", "TV_3", "BAM_3", "VOZ_3",
    )
)

# --- 5.6 METAS_COMISIONES (hoja 'Hoja1$') ---
METAS_COMISIONES_SHEET = "Hoja1$"
METAS_COMISIONES_TABLE = "METAS_COMISIONES"

METAS_COMISIONES_COLUMN_SPEC = (
    ColumnMapping("Plataforma", "Plataforma", CastType.STR),
    ColumnMapping("Cargo", "Cargo", CastType.STR),
    ColumnMapping("Nombre", "Nombre", CastType.STR),
    ColumnMapping("Fibra", "Fibra", CastType.NONE),
    ColumnMapping("Voz", "Voz", CastType.NONE),
    ColumnMapping("Total", "Total", CastType.NONE),
    ColumnMapping("BG_DNI", "BG_DNI", CastType.STR),
    ColumnMapping("PERIODO", "PERIODO", CastType.INT),
    ColumnMapping("DNI", "DNI", CastType.STR),
    # renombrada en el destino: "Señalizacion Total" -> "SEÑALIZACIONES TOTAL"
    ColumnMapping("Señalizacion Total", "SEÑALIZACIONES TOTAL", CastType.NONE),
    ColumnMapping("PUSHER A CARGO", "PUSHER A CARGO", CastType.STR),
)

# --- 5.8 TBL_FUNNEL_VENTAS_Temp (SQL -> SQL, sin Data Conversion) ---
# Fuente: tabla completa [dbo].[TBL_FUNNEL_VENTAS_basev2_temp].
# 'Tramo Ingreso' se lee pero no se mapea al destino (se descarta, igual que
# en el .dtsx original).
FUNNEL_VENTAS_TEMP_SOURCE_TABLE = "TBL_FUNNEL_VENTAS_basev2_temp"
FUNNEL_VENTAS_TEMP_TABLE = "TBL_FUNNEL_VENTAS_Temp"

FUNNEL_VENTAS_TEMP_COLUMN_SPEC = (
    ColumnMapping("Fecha Ingreso", "Fecha Ingreso", CastType.NONE),
    ColumnMapping("Rut Empresa", "Rut Empresa", CastType.NONE),
    ColumnMapping("Nombre Empresa", "Nombre Empresa", CastType.NONE),
    ColumnMapping("Segmento", "Segmento", CastType.NONE),
    ColumnMapping("Servicio", "Servicio", CastType.NONE),
    ColumnMapping("Sub Servicio", "Sub Servicio", CastType.NONE),
    ColumnMapping("STB", "STB", CastType.NONE),
    ColumnMapping("BAF", "BAF", CastType.NONE),
    ColumnMapping("TV", "TV", CastType.NONE),
    ColumnMapping("VOZ", "VOZ", CastType.NONE),
    ColumnMapping("BAM", "BAM", CastType.NONE),
    ColumnMapping("TOTAL INGRESADO", "TOTAL INGRESADO", CastType.NONE),
    ColumnMapping("ESTADO", "ESTADO", CastType.NONE),
    ColumnMapping("MODALIDAD DE INGRESO", "MODALIDAD DE INGRESO", CastType.NONE),
    ColumnMapping("MOTIVO CANCELACION", "MOTIVO CANCELACION", CastType.NONE),
    ColumnMapping("OBS SEGUIMIENTO", "OBS SEGUIMIENTO", CastType.NONE),
    ColumnMapping("TIPO VENTA", "TIPO VENTA", CastType.NONE),
    ColumnMapping("AUDITORIA AUTOINGRESO", "AUDITORIA AUTOINGRESO", CastType.NONE),
    ColumnMapping("OBSERVACION", "OBSERVACION", CastType.NONE),
    ColumnMapping("NRO ENGANCHE", "NRO ENGANCHE", CastType.NONE),
    ColumnMapping("FECHA HABILITACION", "FECHA HABILITACION", CastType.NONE),
    ColumnMapping("FECHA ENGANCHE", "FECHA ENGANCHE", CastType.NONE),
    ColumnMapping("RUT BACK", "RUT BACK", CastType.NONE),
    ColumnMapping("BACKOFFICE", "BACKOFFICE", CastType.NONE),
    ColumnMapping("RUT RAC VENTA", "RUT RAC VENTA", CastType.NONE),
    ColumnMapping("RUT EJECUTIVO", "RUT EJECUTIVO", CastType.NONE),
    ColumnMapping("NOMBRE EJECUTIVO", "NOMBRE EJECUTIVO", CastType.NONE),
    ColumnMapping("SUB SEGMENTO", "SUB SEGMENTO", CastType.NONE),
    ColumnMapping("SUPERVISOR", "SUPERVISOR", CastType.NONE),
    ColumnMapping("Especialista", "Especialista", CastType.NONE),
    ColumnMapping("Pusher", "PUSHER", CastType.NONE),
    ColumnMapping("DNI SUPERVISOR", "DNI supervisor", CastType.NONE),
    ColumnMapping("DNI ESPECIALISTA", "DNI Especialista", CastType.NONE),
    ColumnMapping("Nro de Orden DEM/BELIEVE", "Nro de Orden", CastType.NONE),
    ColumnMapping(
        "SEÑALIZACION // EJECUTIVO DE VENTAS",
        "SEÑALIZACION  EJECUTIVO DE VENTAS",
        CastType.NONE,
    ),
    ColumnMapping("COD_DNI", "DNI EJECUTIVO", CastType.NONE),
    ColumnMapping("FECHA DE EVALUACION", "FECHA DE EVALUACION", CastType.NONE),
)
