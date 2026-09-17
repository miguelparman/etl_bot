"""Orquestador de los 2 paquetes .dtsx migrados: 'CROSS 0101
SSIS_CL_Senalizaciones' y 'CROSS 0102 SSIS_CL_Ventas'.

Llama en orden a las 4 capas del proceso -- extraccion/, validacion/,
transformacion/ y carga/ -- no conoce pyodbc, requests ni ningun otro
detalle de db.py/sharepoint/. 'ejecutar_senalizaciones'/'ejecutar_ventas'
equivalen cada uno a UN paquete .dtsx original; 'ejecutar_todo' los corre en
el orden pedido por el usuario (0101 -> 0102), deteniendose en el primero
que falle (fail-fast), igual que una cadena de pasos de un job SQL Agent.

    CROSS 0101 SSIS_CL_Senalizaciones
        Descargar googledrive señalizaciones (fuera de alcance, ver README)
        TRUNCATE SEÑALIZACIONES -> Data Flow 'TBL_FUNNEL_SENHALIZACIONES' (CSV)
        SP_FUNNEL_SENHALIZACIONES
        UPDATE (corrige DNIs con cero perdido, 19 pares literales)
        Contenedor de secuencias: TRUNCATE -> Data Flow 'TBL_FUNNEL_SENHALIZACIONES_DNI'
            (Excel) -> UPDATE (corrige 'TU DNI' desde la tabla DNI)

    CROSS 0102 SSIS_CL_Ventas (TBL_VENTAS_CROSSELLING_PUSHER_ABORDABLE ya
    viene deshabilitado en el .dtsx original -- no se migra, ver README)
        Contenedor de secuencias 2 (COMISIONES, DNI, METAS -- sin
        dependencia entre si en el .dtsx original; se corren aqui en el
        orden en que aparecen en el paquete):
            COMISIONES: TRUNCATE -> Data Flow 'TBL_VENTAS_RANGO_COMISIONES' (Excel)
            Contenedor de secuencias 1: TRUNCATE -> Data Flow
                'TBL_FUNNEL_SENHALIZACIONES_DNI' (recarga independiente, ver README)
            METAS: TRUNCATE -> Data Flow 'METAS_COMISIONES' (Excel)
        Contenedor de secuencias 1 (BaseV2, Esp, Sup -- paralelos en el
        .dtsx original; se corren aqui en secuencia, el resultado no cambia
        porque son independientes entre si):
            BaseV2: TRUNCATE -> Data Flow 'TBL_FUNNEL_VENTAS_basev2_temp' (Excel)
                -> Tarea Ejecutar SQL (limpieza) -> update DNI
            Contenedor de secuencias (Esp): TRUNCATE -> Data Flow 'TBL_FUNNEL_VENTAS_Esp_temp'
            Sup: TRUNCATE -> Data Flow 'TBL_FUNNEL_VENTAS_Sup_temp'
            UPDATE (completa DNI SUPERVISOR/DNI ESPECIALISTA/COD_DNI, depende
                de que BaseV2+Esp+Sup ya hayan cargado)
        LOCAL: TRUNCATE TBL_FUNNEL_VENTAS_Temp -> Data Flow 'TBL_FUNNEL_VENTAS_Temp'
            (desde basev2_temp) -> DELETE VENTAS2 >= Fecha -> DELETE TEMP < Fecha
            -> INSERT VENTAS2 (desde Temp)

Ver el README para el detalle completo del Control Flow / Data Flow de cada
paquete original.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Callable

import mappings
from carga import loader
from db import DatabaseGateway
from exceptions import PipelineError
from extraccion import extractor
from models import ResultadoPipeline, ResultadoSubPipeline
from sharepoint.reader import SharePointCsvReader, SharePointExcelReader
from transformacion import transformer
from validacion import validator

logger = logging.getLogger("ventas")


@dataclass
class VentasPipeline:
    """Orquesta los 2 sub-pipelines. Ambos escriben unicamente en
    CL_USUARIOS (unico destino real de los 2 .dtsx, ver config.py) y leen
    de la misma carpeta '07 CROSS' de SharePoint."""

    db: DatabaseGateway
    csv_reader: SharePointCsvReader
    excel_reader: SharePointExcelReader

    def ejecutar_senalizaciones(self) -> ResultadoSubPipeline:
        """CROSS 0101 SSIS_CL_Senalizaciones.dtsx."""
        nombre = "senalizaciones"
        filas_por_paso: dict[str, int] = {}

        self._step(nombre, "TRUNCATE SEÑALIZACIONES", loader.truncar_senhalizaciones, self.db)
        df = self._step(nombre, "TBL_FUNNEL_SENHALIZACIONES / extraccion", extractor.extraer_senhalizaciones, self.csv_reader)
        self._step(nombre, "TBL_FUNNEL_SENHALIZACIONES / validacion (columnas)", validator.validar_columnas_senhalizaciones, df)
        df = self._step(
            nombre, "TBL_FUNNEL_SENHALIZACIONES / transformacion (seleccion/renombre)",
            transformer.seleccionar_y_renombrar_senhalizaciones, df,
        )
        df = self._step(
            nombre, "TBL_FUNNEL_SENHALIZACIONES / transformacion (RUT/Nombre Empresa invertidos)",
            transformer.corregir_rut_nombre_invertidos, df,
        )
        df = self._step(
            nombre, "TBL_FUNNEL_SENHALIZACIONES / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_SENHALIZACIONES, "senalizaciones",
        )
        df = self._step(
            nombre, "TBL_FUNNEL_SENHALIZACIONES / transformacion (tipos)",
            transformer.convertir_tipos, df, mappings.COLUMNAS_SENHALIZACIONES,
        )
        filas_por_paso["TBL_FUNNEL_SENHALIZACIONES"] = self._step(
            nombre, "TBL_FUNNEL_SENHALIZACIONES / carga", loader.cargar_senhalizaciones, self.db, df
        )

        self._step(nombre, "SP_FUNNEL_SENHALIZACIONES", transformer.ejecutar_sp_funnel_senhalizaciones, self.db)
        self._step(nombre, "UPDATE (DNI cero perdido)", transformer.corregir_dni_cero_perdido, self.db)

        self._step(nombre, "Contenedor de secuencias / TRUNCATE", loader.truncar_dni_senhalizaciones, self.db)
        df_dni = self._step(
            nombre, "Contenedor de secuencias / TBL_FUNNEL_SENHALIZACIONES_DNI / extraccion",
            extractor.extraer_dni_senhalizaciones, self.excel_reader,
        )
        self._step(nombre, "Contenedor de secuencias / validacion (columnas)", validator.validar_columnas_dni_senhalizaciones, df_dni)
        df_dni = self._step(
            nombre, "Contenedor de secuencias / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df_dni, mappings.COLUMNAS_SENHALIZACIONES_DNI, "senalizaciones",
        )
        filas_por_paso["TBL_FUNNEL_SENHALIZACIONES_DNI"] = self._step(
            nombre, "Contenedor de secuencias / TBL_FUNNEL_SENHALIZACIONES_DNI / carga",
            loader.cargar_dni_senhalizaciones, self.db, df_dni,
        )
        self._step(nombre, "Contenedor de secuencias / UPDATE", transformer.corregir_dni_desde_tabla_dni, self.db)

        logger.info("[senalizaciones] Finalizado: %s", filas_por_paso)
        return ResultadoSubPipeline(nombre=nombre, filas_por_paso=filas_por_paso)

    def ejecutar_ventas(self, fecha: date) -> ResultadoSubPipeline:
        """CROSS 0102 SSIS_CL_Ventas.dtsx ('TBL_VENTAS_CROSSELLING_PUSHER_ABORDABLE'
        ya viene deshabilitado en el .dtsx original -- no se migra, ver README)."""
        nombre = "ventas"
        filas_por_paso: dict[str, int] = {}

        self._cargar_rango_comisiones(nombre, filas_por_paso)
        self._recargar_dni_senhalizaciones(nombre, filas_por_paso)
        self._cargar_metas_comisiones(nombre, filas_por_paso)

        self._cargar_basev2(nombre, filas_por_paso)
        self._cargar_esp(nombre, filas_por_paso)
        self._cargar_sup(nombre, filas_por_paso)
        self._step(nombre, "Contenedor de secuencias 1 / UPDATE (DNI supervisor/especialista/cod)", transformer.completar_dni_sup_esp_cod, self.db)

        self._local(nombre, filas_por_paso, fecha)

        logger.info("[ventas] Finalizado: %s", filas_por_paso)
        return ResultadoSubPipeline(nombre=nombre, filas_por_paso=filas_por_paso)

    def ejecutar_todo(self, fecha: date) -> ResultadoPipeline:
        """Corre los 2 sub-pipelines en el orden declarado (0101 -> 0102). Se
        detiene si alguno lanza PipelineError."""
        resultados = (
            self.ejecutar_senalizaciones(),
            self.ejecutar_ventas(fecha),
        )
        return ResultadoPipeline(resultados=resultados)

    # -- Ventas: Contenedor de secuencias 2 -----------------------------------

    def _cargar_rango_comisiones(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "COMISIONES / TRUNCATE", loader.truncar_ventas_rango_comisiones, self.db)
        df = self._step(nombre, "COMISIONES / extraccion", extractor.extraer_ventas_rango_comisiones, self.excel_reader)
        self._step(nombre, "COMISIONES / validacion", validator.validar_columnas_ventas_rango_comisiones, df)
        df = self._step(
            nombre, "COMISIONES / transformacion (seleccion de columnas)",
            transformer.seleccionar_columnas, df, mappings.COLUMNAS_VENTAS_RANGO_COMISIONES,
        )
        filas_por_paso["TBL_VENTAS_RANGO_COMISIONES"] = self._step(
            nombre, "COMISIONES / carga", loader.cargar_ventas_rango_comisiones, self.db, df
        )

    def _recargar_dni_senhalizaciones(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "Contenedor de secuencias 1 / TRUNCATE", loader.truncar_ventas_dni_senhalizaciones, self.db)
        df = self._step(nombre, "Contenedor de secuencias 1 / extraccion", extractor.extraer_ventas_dni_senhalizaciones, self.excel_reader)
        self._step(nombre, "Contenedor de secuencias 1 / validacion (columnas)", validator.validar_columnas_dni_senhalizaciones, df)
        df = self._step(
            nombre, "Contenedor de secuencias 1 / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_SENHALIZACIONES_DNI, "ventas",
        )
        filas_por_paso["TBL_FUNNEL_SENHALIZACIONES_DNI (Ventas)"] = self._step(
            nombre, "Contenedor de secuencias 1 / carga", loader.cargar_ventas_dni_senhalizaciones, self.db, df
        )

    def _cargar_metas_comisiones(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "METAS / TRUNCATE", loader.truncar_metas_comisiones, self.db)
        df = self._step(nombre, "METAS / extraccion", extractor.extraer_ventas_metas, self.excel_reader)
        self._step(nombre, "METAS / validacion (columnas)", validator.validar_columnas_ventas_metas, df)
        df = self._step(
            nombre, "METAS / transformacion (seleccion de columnas)",
            transformer.seleccionar_columnas, df, mappings.COLUMNAS_VENTAS_METAS_ORIGEN,
        )
        df = self._step(nombre, "METAS / transformacion (tipos)", transformer.convertir_tipos_metas, df)
        df = self._step(
            nombre, "METAS / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_VENTAS_METAS_TEXTO, "ventas",
        )
        filas_por_paso["METAS_COMISIONES"] = self._step(nombre, "METAS / carga", loader.cargar_metas_comisiones, self.db, df)

    # -- Ventas: Contenedor de secuencias 1 -----------------------------------

    def _cargar_basev2(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "BaseV2 / TRUNCATE", loader.truncar_ventas_basev2, self.db)
        df = self._step(nombre, "BaseV2 / extraccion", extractor.extraer_ventas_basev2, self.excel_reader)
        self._step(nombre, "BaseV2 / validacion (columnas)", validator.validar_columnas_ventas_basev2, df)
        df = self._step(
            nombre, "BaseV2 / transformacion (seleccion de columnas)",
            transformer.seleccionar_columnas, df, tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_BASEV2),
        )
        df = self._step(
            nombre, "BaseV2 / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_VENTAS_BASEV2, "ventas",
        )
        df = self._step(nombre, "BaseV2 / transformacion (tipos)", transformer.convertir_tipos, df, mappings.COLUMNAS_VENTAS_BASEV2)
        df = self._step(nombre, "BaseV2 / transformacion (columnas post-carga)", transformer.agregar_columnas_post_carga_basev2, df)
        filas_por_paso["TBL_FUNNEL_VENTAS_basev2_temp"] = self._step(
            nombre, "BaseV2 / carga", loader.cargar_ventas_basev2, self.db, df
        )
        self._step(nombre, "BaseV2 / Tarea Ejecutar SQL (limpieza)", transformer.limpiar_y_completar_basev2, self.db)
        self._step(nombre, "BaseV2 / update DNI", transformer.actualizar_rut_ejecutivo_desde_tabla_dni, self.db)

    def _cargar_esp(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "Esp / TRUNCATE", loader.truncar_ventas_esp, self.db)
        df = self._step(nombre, "Esp / extraccion", extractor.extraer_ventas_esp, self.excel_reader)
        self._step(nombre, "Esp / validacion (columnas)", validator.validar_columnas_ventas_esp, df)
        df = self._step(
            nombre, "Esp / transformacion (seleccion de columnas)",
            transformer.seleccionar_columnas, df, tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_ESP),
        )
        df = self._step(
            nombre, "Esp / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_VENTAS_ESP, "ventas",
        )
        filas_por_paso["TBL_FUNNEL_VENTAS_Esp_temp"] = self._step(nombre, "Esp / carga", loader.cargar_ventas_esp, self.db, df)

    def _cargar_sup(self, nombre: str, filas_por_paso: dict[str, int]) -> None:
        self._step(nombre, "Sup / TRUNCATE", loader.truncar_ventas_sup, self.db)
        df = self._step(nombre, "Sup / extraccion", extractor.extraer_ventas_sup, self.excel_reader)
        self._step(nombre, "Sup / validacion (columnas)", validator.validar_columnas_ventas_sup, df)
        df = self._step(
            nombre, "Sup / transformacion (seleccion de columnas)",
            transformer.seleccionar_columnas, df, tuple(c.nombre for c in mappings.COLUMNAS_VENTAS_SUP),
        )
        df = self._step(
            nombre, "Sup / transformacion (vaciar valores muy largos)",
            transformer.vaciar_valores_que_excedan_ancho, df, mappings.COLUMNAS_VENTAS_SUP, "ventas",
        )
        filas_por_paso["TBL_FUNNEL_VENTAS_Sup_temp"] = self._step(nombre, "Sup / carga", loader.cargar_ventas_sup, self.db, df)

    # -- Ventas: LOCAL ---------------------------------------------------------

    def _local(self, nombre: str, filas_por_paso: dict[str, int], fecha: date) -> None:
        self._step(nombre, "LOCAL / TRUNCATE TBL_FUNNEL_VENTAS_Temp", loader.truncar_ventas_temp, self.db)
        df = self._step(nombre, "LOCAL / TBL_FUNNEL_VENTAS_Temp / extraccion", extractor.extraer_ventas_basev2_temp, self.db)
        df = self._step(nombre, "LOCAL / TBL_FUNNEL_VENTAS_Temp / transformacion (renombre)", transformer.renombrar_basev2_a_temp, df)
        filas_por_paso["TBL_FUNNEL_VENTAS_Temp"] = self._step(
            nombre, "LOCAL / TBL_FUNNEL_VENTAS_Temp / carga", loader.cargar_ventas_temp, self.db, df
        )
        filas_por_paso["DELETE VENTAS2 >="] = self._step(nombre, "LOCAL / DELETE VENTAS2 >=", transformer.borrar_ventas2_desde_fecha, self.db, fecha)
        filas_por_paso["DELETE TEMP <"] = self._step(nombre, "LOCAL / DELETE TEMP <", transformer.borrar_temp_anterior_a_fecha, self.db, fecha)
        filas_por_paso["INSERT VENTAS2"] = self._step(nombre, "LOCAL / INSERT VENAS2", transformer.insertar_ventas2_desde_temp, self.db)

    def _step(self, pipeline: str, descripcion: str, accion: Callable, *args):
        logger.info("[%s] %s", pipeline, descripcion)
        try:
            return accion(*args)
        except Exception as exc:  # noqa: BLE001 - se re-lanza tipado como PipelineError
            raise PipelineError(pipeline, descripcion, exc) from exc
