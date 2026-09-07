"""
Reintentos centralizados con backoff exponencial progresivo.

MAX_RETRIES es el numero de REINTENTOS tras el primer intento fallido (con
MAX_RETRIES=3 se hacen hasta 4 intentos en total). El retraso entre
intentos crece como base_delay_s, base_delay_s*2, base_delay_s*4, ... Si la
excepcion trae adjunta una respuesta HTTP 429 con cabecera Retry-After
(caso tipico de throttling de Microsoft Graph), se respeta ese valor en
vez del backoff calculado.

No se reintenta indefinidamente: al agotar los intentos, se relanza la
ultima excepcion sin modificar.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from app.logger import log

T = TypeVar("T")


def _retry_after_seconds(exc: BaseException) -> float | None:
    response = getattr(exc, "response", None)
    if response is None or getattr(response, "status_code", None) != 429:
        return None
    header = getattr(response, "headers", {}).get("Retry-After")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def retry_call(fn: Callable[[], T], *, max_retries: int, base_delay_s: float = 2.0, what: str = "la operacion") -> T:
    total_attempts = max_retries + 1
    for attempt in range(1, total_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == total_attempts:
                log.error("%s fallo tras %d intento(s); no quedan mas reintentos.", what, attempt)
                raise
            delay = _retry_after_seconds(exc)
            if delay is None:
                delay = base_delay_s * (2 ** (attempt - 1))
            log.warning(
                "%s fallo (intento %d de %d): %s. Reintentando en %.0fs...",
                what,
                attempt,
                total_attempts,
                exc,
                delay,
            )
            time.sleep(delay)
    raise AssertionError("retry_call: bucle de reintentos termino sin retornar ni relanzar")
