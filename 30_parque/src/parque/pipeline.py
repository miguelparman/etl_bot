"""Orquestador del pipeline de Parque.

Migracion de SSIS_Chile_parque.dtsx. El .dtsx original corre 'PQ FIJO I' y
'PQ MOVIL I' en paralelo (ThreadHint 0/1 dentro del Sequence 'SERVIDOR'):
son ramas completamente independientes entre si (sin join/lookup cruzado,
sin precedence constraint que las conecte), asi que un fallo en una NO
detiene a la otra. Se preserva ese aislamiento aqui aunque la ejecucion sea
secuencial (no en threads separados): cada rama se intenta por completo
antes de propagar cualquier error.

Dentro de cada rama, en cambio, SI hay una dependencia estricta (precedence
"On Success" en el .dtsx original): la sub-rama 'II' (HISTORICO) solo corre
si la sub-rama 'I' (_ACTUAL) termino en exito.

    PQ FIJO I    TRUNCATE -> Data Flow (Origen SharePoint/CSV -> Destino TBL_PARQUE_FIJO_ACTUAL)
      |
      v (On Success)
    PQ FIJO II   DELETE WHERE PERIODO=? -> Data Flow (Fase 2: TBL_PARQUE_FIJO_ACTUAL -> TBL_PARQUE_FIJO_HISTORICO)

    PQ MOVIL I / PQ MOVIL II: identico, en paralelo/independiente de FIJO.

A diferencia del .dtsx original, el Data Flow de 'PQ FIJO II'/'PQ MOVIL II'
no vuelve a leer Externos_Frac (ni SharePoint): lee desde la tabla _ACTUAL
que la sub-rama 'I' acaba de cargar en esta misma corrida (ver README,
seccion 'Fase 2', y carga/loader.insertar_historico_desde_actual).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from carga import loader
from db import DatabaseGateway
from exceptions import PipelineError
from extraccion import extractor
from models import (
    ParqueFlowSpec,
    ResultadoFlujo,
    ResultadoHistorico,
    ResultadoPipeline,
    ResultadoRama,
)
from sharepoint.reader import SharePointCsvReader
from transformacion import transformer
from validacion import validator

logger = logging.getLogger("parque")


@dataclass
class ParquePipeline:
    """Orquesta las 2 ramas independientes (FIJO, MOVIL) del .dtsx original,
    cada una: extraccion -> validacion -> transformacion -> carga (_ACTUAL),
    seguido de DELETE -> carga (_HISTORICO) si _ACTUAL cargo correctamente."""

    name = "parque"

    db: DatabaseGateway
    sharepoint_reader: SharePointCsvReader
    fijo_spec: ParqueFlowSpec
    movil_spec: ParqueFlowSpec

    def run(self, periodo: str) -> ResultadoPipeline:
        logger.info("[Parque] Inicio del pipeline (periodo=%s)", periodo)

        errores: list[PipelineError] = []
        resultado_fijo: ResultadoRama | None = None
        resultado_movil: ResultadoRama | None = None

        try:
            resultado_fijo = self._ejecutar_rama(self.fijo_spec, periodo)
        except PipelineError as exc:
            errores.append(exc)
            logger.error(
                "[Parque] Rama '%s' fallo; se continua con la rama MOVIL (independientes "
                "en el .dtsx original, sin precedence constraint entre ellas): %s",
                self.fijo_spec.nombre,
                exc,
            )

        try:
            resultado_movil = self._ejecutar_rama(self.movil_spec, periodo)
        except PipelineError as exc:
            errores.append(exc)
            logger.error("[Parque] Rama '%s' fallo: %s", self.movil_spec.nombre, exc)

        if errores:
            # Se propaga el primer error (FIJO antes que MOVIL, mismo orden
            # declarado) despues de haber intentado AMBAS ramas -- a
            # diferencia de un pipeline con corto-circuito, aqui una rama
            # fallida no le impide correr a la otra.
            raise errores[0]

        resultado = ResultadoPipeline(periodo=periodo, fijo=resultado_fijo, movil=resultado_movil)
        logger.info("[Parque] Pipeline finalizado correctamente: %s", resultado)
        return resultado

    def _ejecutar_rama(self, spec: ParqueFlowSpec, periodo: str) -> ResultadoRama:
        # 'PQ FIJO II'/'PQ MOVIL II' dependen ("On Success") de que su 'I'
        # correspondiente haya terminado sin error: si _ejecutar_actual
        # lanza, no se llega a intentar _ejecutar_historico (se propaga tal
        # cual, sin capturar aqui).
        resultado_actual = self._ejecutar_actual(spec, periodo)
        resultado_historico = self._ejecutar_historico(spec, periodo)
        return ResultadoRama(actual=resultado_actual, historico=resultado_historico)

    def _ejecutar_actual(self, spec: ParqueFlowSpec, periodo: str) -> ResultadoFlujo:
        # El TRUNCATE original es una tarea separada e incondicional, previa
        # al Data Flow (precedence "On Success"): se ejecuta primero y, si
        # algo falla despues, la tabla queda vacia -- se preserva ese orden
        # tal cual (ver README, 'Notas de fidelidad').
        self._step(spec.nombre, "TRUNCATE", lambda: loader.truncar_tabla(self.db, spec))

        df_csv = self._step(
            spec.nombre,
            "Origen OLE DB (SharePoint/CSV)",
            lambda: extractor.extraer(self.sharepoint_reader, spec),
        )
        df_periodo = self._step(
            spec.nombre,
            "Filtro WHERE periodo = ? / validacion de columnas y largos",
            lambda: validator.validar(df_csv, spec, periodo),
        )
        df_final = self._step(
            spec.nombre,
            "Transformacion (reordenar columnas)",
            lambda: transformer.reordenar_columnas(df_periodo, spec),
        )
        filas_cargadas = self._step(
            spec.nombre,
            "Destino OLE DB",
            lambda: loader.cargar_actual(self.db, spec, df_final),
        )

        return ResultadoFlujo(
            nombre=spec.nombre,
            filas_csv=len(df_csv),
            filas_periodo=len(df_periodo),
            filas_cargadas=filas_cargadas,
        )

    def _ejecutar_historico(self, spec: ParqueFlowSpec, periodo: str) -> ResultadoHistorico:
        filas_purgadas = self._step(
            spec.nombre_historico,
            "DELETE WHERE PERIODO = ?",
            lambda: loader.borrar_historico_periodo(self.db, spec, periodo),
        )
        filas_insertadas = self._step(
            spec.nombre_historico,
            "Data Flow (desde _ACTUAL)",
            lambda: loader.insertar_historico_desde_actual(self.db, spec, periodo),
        )
        return ResultadoHistorico(
            nombre=spec.nombre_historico,
            filas_purgadas=filas_purgadas,
            filas_insertadas=filas_insertadas,
        )

    def _step(self, flujo: str, paso: str, action: Callable):
        descripcion = f"{flujo} / {paso}"
        logger.info("[Parque] %s", descripcion)
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - se re-lanza tipado como PipelineError
            raise PipelineError(self.name, descripcion, exc) from exc
