"""Permite 'import config', 'import db', 'import contactos...' etc. al correr
pytest desde cualquier directorio (mismo patrón que main.py con sys.path)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
