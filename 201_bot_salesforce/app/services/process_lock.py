"""
Lock de proceso basado en archivo, para evitar que dos ejecuciones del bot
procesen los mismos informes en paralelo (p.ej. una manual y la programada
solapandose). Esto ya causo una colision real: dos instancias compartiendo
la carpeta downloads/ y subiendo el mismo archivo a SharePoint a la vez
(HTTP 409 nameAlreadyExists).

Politica: la ejecucion mas nueva gana. Si al arrancar encuentra una
ejecucion previa todavia viva, la termina (con todo su arbol de procesos,
para no dejar huerfano el navegador) antes de continuar.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from app.logger import log

_KILL_WAIT_TIMEOUT_S = 10
_KILL_WAIT_POLL_S = 0.5


class ProcessLock:
    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path

    def acquire(self) -> None:
        if self._lock_path.exists():
            pid_text = self._lock_path.read_text(encoding="utf-8").strip()
            pid = int(pid_text) if pid_text.isdigit() else None

            if pid is not None and _is_process_running(pid):
                log.warning(
                    "Ejecucion previa aun activa (PID %s); se termina antes de continuar.",
                    pid,
                )
                _kill_process_tree(pid)
                if not _wait_until_stopped(pid):
                    log.warning(
                        "El proceso previo (PID %s) no confirmo su cierre tras %ss; se continua igual.",
                        pid,
                        _KILL_WAIT_TIMEOUT_S,
                    )
            else:
                log.warning(
                    "Se encontro un lock huerfano (PID %s ya no existe); se ignora y se continua.",
                    pid_text,
                )

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path.write_text(str(os.getpid()), encoding="utf-8")

    def release(self) -> None:
        try:
            self._lock_path.unlink()
        except FileNotFoundError:
            pass


def _is_process_running(pid: int) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return str(pid) in result.stdout


def _kill_process_tree(pid: int) -> None:
    # /T tambien mata a los hijos (el navegador de Playwright), no solo al
    # proceso python; sin esto quedaria un chrome.exe huerfano consumiendo
    # recursos.
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _wait_until_stopped(pid: int) -> bool:
    deadline = time.monotonic() + _KILL_WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        if not _is_process_running(pid):
            return True
        time.sleep(_KILL_WAIT_POLL_S)
    return not _is_process_running(pid)
