"""Punto de entrada del proyecto.

Ejemplos:
    python main.py senalizaciones
    python main.py ventas --fecha 2026-08-01
    python main.py all --fecha 2026-08-01
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from etl_chile.presentation.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
